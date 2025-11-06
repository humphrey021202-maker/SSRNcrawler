from __future__ import annotations
import sys
import re
from pathlib import Path
from typing import List, Optional, Set
from bs4 import BeautifulSoup
import csv
import unicodedata

# Optional encoding detection (if installed)
try:
    from charset_normalizer import from_bytes as detect_from_bytes
except Exception:
    detect_from_bytes = None

DELIM = ';'  # 英文分号
ABSTRACT_ID_RE = re.compile(r"abstract_id=(\d+)")

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)

def read_html_text(path: Path) -> str:
    """Robustly read HTML file with fallback decoding."""
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

def find_abstract_id(href: str) -> Optional[str]:
    if not href:
        return None
    m = ABSTRACT_ID_RE.search(href)
    return m.group(1) if m else None

def parse_one_list_html(path: Path) -> List[dict]:
    html = read_html_text(path)
    soup = BeautifulSoup(html, 'lxml')  # 若没有 lxml，可改为 'html.parser'
    out = []

    for paper in soup.select('div.paper'):
        title_tag = paper.select_one('.paper-info .title a, .title a')
        title = normalize_space(title_tag.get_text()) if title_tag else ''
        href = title_tag['href'] if (title_tag and title_tag.has_attr('href')) else ''
        abstract_id = find_abstract_id(href) or ''

        posted_date = ''
        for sp in paper.select('.stats span'):
            txt = sp.get_text(strip=True)
            if txt.lower().startswith('posted'):
                posted_date = normalize_space(txt)
                break

        authors = [normalize_space(nfc(a.get_text())) for a in paper.select('.authors a')]

        # 直接拉取 affiliations 原始纯文本（不做拆分/识别）
        aff_raw_tag = paper.select_one('.affiliations')
        aff_raw = normalize_space(nfc(aff_raw_tag.get_text())) if aff_raw_tag else ''

        out.append({
            'abstract_id': abstract_id,
            'title': title,
            'posted': posted_date,
            'authors': DELIM.join(authors) if authors else '',
            'affiliations': aff_raw,         # 直接原样写入
            'source_file': str(path.name),
        })
    return out

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

    # ===== 去重（按 abstract_id）=====
    total_rows = len(rows)
    seen: Set[str] = set()
    dedup_rows: List[dict] = []
    for r in rows:
        aid = (r.get('abstract_id') or '').strip()
        if aid and aid in seen:
            continue
        if aid:
            seen.add(aid)
        dedup_rows.append(r)
    dedup_count = len(dedup_rows)

    # ===== 写入 CSV（仅去重后的数据）=====
    fieldnames = ['abstract_id', 'title', 'posted', 'authors', 'affiliations', 'source_file']
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in dedup_rows:
            # 统一 NFC & 去除多余空白
            cleaned = {}
            for k, v in r.items():
                if isinstance(v, str):
                    cleaned[k] = nfc(normalize_space(v))
                else:
                    cleaned[k] = v
            w.writerow(cleaned)

    # ===== 汇总输出 =====
    print("\n===== 统计汇总 =====")
    print(f"📄 原始解析记录总数：{total_rows}")
    print(f"🧹 按 abstract_id 去重后输出记录数：{dedup_count}")
    if total_rows > 0:
        dup_num = total_rows - dedup_count
        rate = dup_num / total_rows * 100
        print(f"🔁 重复条数：{dup_num}（约 {rate:.2f}%）")

    return out_csv

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python parse_ssrn_dir_v2.py <folder_with_html_files>')
        sys.exit(1)
    output = main(sys.argv[1])
    print(f"\n✅ Done. CSV saved to: {output}")
