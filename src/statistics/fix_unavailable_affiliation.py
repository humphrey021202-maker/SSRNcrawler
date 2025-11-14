#INPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law.csv"
#OUTPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law_with_fixed_affil.csv"
import asyncio
import re
import time
import random

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ===== 基本配置 =====
INPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law_with_fixed_affil.csv"
OUTPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law_with_fixed_affil11.csv"

COL_ABSTRACT_ID = "abstract_id"
COL_AUTHORS = "authors"
COL_AFFIL = "affiliations"

BASE_URL = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id={}"


# ===== 工具函数 =====

def normalize(s: str) -> str:
    s = s or ""
    s = re.sub(r"\s+", " ", s.strip())
    return s.lower()


def split_authors(authors_str: str) -> list[str]:
    """按你 CSV 里实际格式来改。
    这里假设 authors 用 ';' 或 ',' 分隔。"""
    if not isinstance(authors_str, str):
        return []
    parts = re.split(r"\s*;\s*|\s*,\s*", authors_str.strip())
    parts = [p for p in parts if p]
    return parts


def is_bad_affiliation(affil) -> bool:
    """
    只判断三种情况：
    1) 为空 / NaN
    2) 用 and 开头（忽略前后空格、大小写）
    3) 用逗号开头（忽略前后空格）
    """
    # 情况 1：不是字符串（NaN 之类）就当坏
    if not isinstance(affil, str):
        return True

    # 去掉首尾空白（包括 \t、\n、全角空格等）
    s = affil.strip()
    if not s:
        return True

    # 为了更保险，再单独拿掉左侧空白做 startswith 判断
    s_left = affil.lstrip()
    s_left_lower = s_left.lower()

    # 情况 2：以 and 开头（可以是 "and XXX"、"And XXX"、"AND, XXX" 等）
    if s_left_lower.startswith("and "):      # and 后面是空格
        return True
    if s_left_lower.startswith("and,"):      # and 后面直接逗号
        return True
    if s_left_lower == "and":                # 只剩一个 and
        return True

    # 情况 3：以逗号开头（", XXX"）
    if s_left.startswith(","):
        return True

    return False



def parse_affiliations_from_html(html: str, authors: list[str]) -> str | None:
    """从整页 HTML 文本里，根据作者行去找机构行。"""
    if not html or not authors:
        return None

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)

    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return None

    norm_authors = [normalize(a) for a in authors]
    first_author_norm = norm_authors[0]

    # 找到第一个作者出现的位置
    start_idx = None
    for i, ln in enumerate(lines):
        if normalize(ln) == first_author_norm:
            start_idx = i
            break
    if start_idx is None:
        # 放宽一点：包含完整名字也算
        for i, ln in enumerate(lines):
            if first_author_norm in normalize(ln):
                start_idx = i
                break
    if start_idx is None:
        print("    !! 在页面中找不到第一个作者名")
        return None

    lines_after = lines[start_idx:]

    collected_affils: list[str] = []
    i = 0
    while i < len(lines_after):
        ln = lines_after[i]
        n_ln = normalize(ln)

        if n_ln in norm_authors:
            j = i + 1
            aff_lines = []
            while j < len(lines_after):
                ln2 = lines_after[j]
                n_ln2 = normalize(ln2)

                if n_ln2 in norm_authors:
                    break
                if "date written" in n_ln2 or n_ln2.startswith("abstract"):
                    break

                # 可选：略过明显是期刊信息的行
                if n_ln2.startswith("journal of ") or "pages posted" in n_ln2:
                    j += 1
                    continue

                aff_lines.append(ln2)
                j += 1

            aff = " ".join(aff_lines).strip()
            if aff:
                collected_affils.append(aff)
            i = j
        else:
            i += 1

    if not collected_affils:
        return None

    # 去重 + 保序
    seen = set()
    uniq = []
    for a in collected_affils:
        if a not in seen:
            seen.add(a)
            uniq.append(a)

    return "; ".join(uniq)


# ===== 主流程（异步） =====

async def main_async():
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    print(f"读取到 {len(df)} 行数据")

    # 找出需要修补的行索引
    bad_indices: list[int] = []
    for idx, row in df.iterrows():
        affil = row.get(COL_AFFIL, "")
        if is_bad_affiliation(affil):
            bad_indices.append(idx)

    print(f"共发现 {len(bad_indices)} 行 affiliations 需要修补。")

    if not bad_indices:
        print("没有需要修补的行，结束。")
        return

    fixed_count = 0
    error_count = 0

    async with async_playwright() as p:
        # 你可以改成 p.firefox / p.webkit
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context()
        page = await context.new_page()

        # 先让你在这个浏览器里登录一次 SSRN
        print("正在打开 SSRN 首页，请在弹出的浏览器中手动登录（如有需要）...")
        await page.goto("https://www.ssrn.com/index.cfm/en/", wait_until="domcontentloaded")
        input("登录完成后，在终端按 Enter 继续...")

        for idx in bad_indices:
            human_row = idx + 2  # Excel 中的数据行号（第1行为表头）
            abstract_id = str(df.at[idx, COL_ABSTRACT_ID])
            authors_str = df.at[idx, COL_AUTHORS]
            authors = split_authors(authors_str)

            if not authors:
                print(f"\n=== 第 {human_row} 行 abstract_id={abstract_id}：authors 为空，跳过 ===")
                continue

            old_affil = df.at[idx, COL_AFFIL]
            print(f"\n=== 修补第 {human_row} 行 (abstract_id={abstract_id}) ===")
            print(f"  原 affiliations: {old_affil!r}")

            url = BASE_URL.format(abstract_id)
            try:
                print(f"  -> 打开页面 {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # 稍微等一等，防止还在异步加载
                await page.wait_for_timeout(2000)

                html = await page.content()

                new_affil = parse_affiliations_from_html(html, authors)
                if not new_affil:
                    print("  !! 未能从页面解析出机构信息")
                    error_count += 1
                else:
                    print(f"  新 affiliations: {new_affil!r}")
                    df.at[idx, COL_AFFIL] = new_affil
                    fixed_count += 1

                # 对 SSRN 温柔一点，随机 sleep
                sleep_s = 2 + random.random() * 3
                print(f"  休息 {sleep_s:.1f} 秒...")
                await page.wait_for_timeout(int(sleep_s * 1000))

            except Exception as e:
                print(f"  !! 处理 abstract_id={abstract_id} 时出错: {e}")
                error_count += 1

        await browser.close()

    print(f"\n修补完成：成功修补 {fixed_count} 行，出错 {error_count} 行。")
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"结果已保存到 {OUTPUT_CSV}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

