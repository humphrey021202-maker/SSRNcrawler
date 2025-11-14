from __future__ import annotations
import sys
import re
from pathlib import Path
from typing import List, Optional, Set
from bs4 import BeautifulSoup
import csv
import unicodedata

# 可选编码探测
try:
    from charset_normalizer import from_bytes as detect_from_bytes
except Exception:
    detect_from_bytes = None

DELIM = ';'  # 多作者分隔
WILEY_BASE = "https://onlinelibrary.wiley.com"
WILEY_EXCLUDE_TITLES = {"Issue Information", "IN THIS ISSUE"}  # 严格等值过滤

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)

def read_html_text(path: Path) -> str:
    """稳健读取本地 HTML"""
    raw = path.read_bytes()
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        if detect_from_bytes is not None:
            best = detect_from_bytes(raw).best()
            txt = str(best) if best is not None else raw.decode('latin-1', errors='replace')
        else:
            txt = raw.decode('latin-1', errors='replace')
    return nfc(txt)

def parse_wiley_list_html(soup: BeautifulSoup, source_file: str) -> List[dict]:
    """
    解析 Wiley TOC 页面的每条文章卡片，返回结构化记录
    选择器说明（以当前 Wiley TOC DOM 为准）：
      - 卡片：div.issue-item
      - 标题与链接：a.issue-item__title（href 通常以 /doi/ 开头）
      - 作者：.loa .author-style（多作者）
      - 页码：li.page-range span:nth-of-type(2)
      - 出版日期：li.ePubDate span:nth-of-type(2)（即 First Published）
    """
    out: List[dict] = []

    for item in soup.select("div.issue-item"):
        a = item.select_one("a.issue-item__title")
        if not a:
            continue

        title = normalize_space(a.get_text())
        # 过滤刊讯/目录类占位项
        if title in WILEY_EXCLUDE_TITLES:
            continue

        href = a.get("href", "")
        # 相对链接补全成绝对 URL
        if href.startswith("/"):
            url = WILEY_BASE + href
        else:
            url = href or ""

        # 作者
        authors = [normalize_space(x.get_text()) for x in item.select(".loa .author-style")]
        authors_str = DELIM.join([nfc(x) for x in authors]) if authors else ""

        # 页码（如 449-470）
        pages_span = item.select_one("li.page-range span:nth-of-type(2)")
        pages = normalize_space(pages_span.get_text()) if pages_span else ""

        # 出版日期（First Published: 27 July 2025）
        pub_span = item.select_one("li.ePubDate span:nth-of-type(2)")
        published = normalize_space(pub_span.get_text()) if pub_span else ""

        out.append({
            "id": url,          # 唯一标识：文章 URL
            "title": title,
            "authors": authors_str,
            "pages": pages,
            "published": published,
            "source_file": source_file,
        })

    return out

def parse_one_list_html(path: Path) -> List[dict]:
    html = read_html_text(path)
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception:
        soup = BeautifulSoup(html, 'html.parser')
    return parse_wiley_list_html(soup, path.name)

def main(input_dir: str) -> Path:
    root = Path(input_dir).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    result_dir = root.parent / 'result'
    result_dir.mkdir(parents=True, exist_ok=True)
    out_csv = result_dir / f"{root.name}.csv"

    files: List[Path] = sorted(root.rglob('*.html'))
    total_files = len(files)
    if total_files == 0:
        print("⚠️ 未在该目录下找到任何 .html 文件。")
        return out_csv

    print(f"🔎 共发现 {total_files} 个 HTML 文件，将开始解析……")
    last_dir: Optional[Path] = None
    rows: List[dict] = []

    for idx, p in enumerate(files, start=1):
        if p.parent != last_dir:
            last_dir = p.parent
            if last_dir != root:
                print(f"📂 正在扫描子目录：{last_dir}")
        rel = p.relative_to(root)
        print(f"[{idx}/{total_files}] 解析：{rel}")
        try:
            rows.extend(parse_one_list_html(p))
        except Exception as e:
            print(f"❌ 解析失败（跳过）{rel}: {e}")

    # ===== 去重（按 id，即 URL）=====
    total_rows = len(rows)
    seen: Set[str] = set()
    dedup_rows: List[dict] = []
    for r in rows:
        rid = (r.get('id') or '').strip()
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        dedup_rows.append(r)

    # ===== 写入 CSV =====
    fieldnames = ['id', 'title', 'authors', 'pages', 'published', 'source_file']
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in dedup_rows:
            cleaned = {}
            for k, v in r.items():
                if isinstance(v, str):
                    cleaned[k] = nfc(normalize_space(v))
                else:
                    cleaned[k] = v
            w.writerow(cleaned)

    # ===== 汇总 =====
    print("\n===== 统计汇总 =====")
    print(f"📄 原始解析记录总数：{total_rows}")
    print(f"🧹 去重后输出记录数：{len(dedup_rows)}")
    if total_rows > 0:
        dup_num = total_rows - len(dedup_rows)
        rate = dup_num / total_rows * 100
        print(f"🔁 重复条数：{dup_num}（约 {rate:.2f}%）")

    return out_csv

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python parse_wiley_dir.py <folder_with_html_files>')
        sys.exit(1)
    output = main(sys.argv[1])
    print(f"\n✅ Done. CSV saved to: {output}")

