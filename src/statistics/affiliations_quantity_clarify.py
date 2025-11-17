

from __future__ import annotations
import pandas as pd
import re

# ======== 配置区：根据需要修改 ========
INPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law_with_fixed_affil11.csv"
OUTPUT_CSV = "E:/SSRNPaperResearch/data/Biorn/result/Bio_law_clarify11.csv"

AUTH_COL = "authors"        # 作者列名（用分号 ; 分隔）
AFFIL_COL = "affiliations"  # 机构列名（用逗号 , 分隔）
ENCODING = "utf-8-sig"
# ===================================


AND_PATTERN = re.compile(r"\band\b", re.IGNORECASE)


def split_authors_field(text: str) -> list[str]:
    """
    authors 列：用分号 ';' 拆分，去掉两侧空格，过滤空字符串。
    """
    if pd.isna(text):
        return []
    parts = [p.strip() for p in str(text).split(";")]
    return [p for p in parts if p]


def split_affil_field(text: str) -> list[str]:
    """
    affiliations 列：用逗号 ',' 拆分，去掉两侧空格，过滤空字符串。
    """
    if pd.isna(text):
        return []
    parts = [p.strip() for p in str(text).split(",")]
    return [p for p in parts if p]


def join_affil_field(items: list[str]) -> str:
    """
    affiliations 修复后再合并：用 ', ' 连接回字符串。
    """
    return ", ".join(items)


def try_fix_last_affil_with_and(authors: list[str], affils: list[str]) -> tuple[list[str], str]:
    """
    如果作者数量和机构数量不等，尝试：
    - 当最后一个 affiliation 中有且仅有一个 'and'
    - 且作者数量 = 机构数量 + 1
    则在 'and' 处拆分最后一个 affiliation。

    返回：(新的 affils 列表, mark)
    mark 可能为：
      - ""                    : 数量一致或修复成功
      - "multi_and_last_affil": 最后一个机构中 and 超过 1 个
      - "mismatch_no_affiliation" / "mismatch_no_and" /
        "mismatch_count_not_n_affil_plus_1" / "mismatch_split_empty_side" /
        "mismatch_after_split_still_neq" 等其他 mismatch 情况
    """
    n_auth = len(authors)
    n_affil = len(affils)

    mark = ""

    # 数量一致，不需要处理
    if n_auth == n_affil:
        return affils, mark

    # 没任何机构，但有作者
    if n_affil == 0:
        return affils, "mismatch_no_affiliation"

    last = affils[-1]
    last_lower = last.lower()

    # 统计 'and' 出现次数（按单词匹配）
    and_occurs = len(AND_PATTERN.findall(last_lower))

    if and_occurs == 0:
        # 最后一个里根本没有 and，但数量不匹配
        return affils, "mismatch_no_and"

    if and_occurs > 1:
        # 多于一个 and，先不乱拆，标记出来
        return affils, "multi_and_last_affil"

    # and 只出现 1 次
    # 只有当作者数 = 机构数 + 1 时，我们才尝试用 and 拆出一个新的机构
    if n_auth != n_affil + 1:
        return affils, "mismatch_count_not_n_affil_plus_1"

    # 找到 " and " 的位置（优先带空格形式，避免拆到单词内部）
    idx = last_lower.find(" and ")
    add_len = 5  # len(" and ")

    if idx == -1:
        # 没有 ' and '，可能是 'and ' / ' and,' 等，退而求其次
        m = AND_PATTERN.search(last_lower)
        if not m:
            return affils, "mismatch_and_not_found_again"
        idx = m.start()
        add_len = len(m.group(0))

    left = last[:idx].rstrip(" ,;")
    right = last[idx + add_len:].lstrip(" ,;")

    if not left or not right:
        # 某一边为空串，不强行修复
        return affils, "mismatch_split_empty_side"

    # 构造新的 affils 列表
    new_affils = affils[:-1] + [left, right]

    # 再检查一次数量是否真的修复了
    if len(new_affils) != n_auth:
        return new_affils, "mismatch_after_split_still_neq"

    # 修复成功
    return new_affils, ""


def replace_last_comma_with_dash(text: str) -> str:
    """
    把字符串中最后一个逗号 ',' 替换为 ' -'（注意 '-' 前有空格）。
    如果没有逗号，返回原文。
    """
    if pd.isna(text):
        return text
    s = str(text)
    pos = s.rfind(",")
    if pos == -1:
        return s
    # 保留逗号后面的内容，只把逗号替换成 ' -'
    return s[:pos] + " -" + s[pos + 1:]


def main() -> None:
    print(f"读取 CSV: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, encoding=ENCODING)

    if AUTH_COL not in df.columns or AFFIL_COL not in df.columns:
        raise ValueError(f"CSV 中必须包含列 '{AUTH_COL}' 和 '{AFFIL_COL}'")

    new_affil_col: list[str] = []
    marks: list[str] = []

    total_rows = len(df)
    fixed_count = 0
    has_mark_count = 0

    for idx, row in df.iterrows():
        authors = split_authors_field(row[AUTH_COL])
        base_affil_str = row[AFFIL_COL]

        # 对于每一行，允许最多两轮“最后逗号替换为 ' -'”的修复尝试
        attempts = 0
        final_mark = ""
        final_affils = None

        while attempts <= 2:
            affils = split_affil_field(base_affil_str)
            new_affils, mark = try_fix_last_affil_with_and(authors, affils)

            # 情况一：不是 mismatch_no_and，直接接受（包括 ""、其他 mark）
            if mark != "mismatch_no_and":
                final_mark = mark
                final_affils = new_affils
                break

            # 情况二：是 mismatch_no_and，执行“最后一个逗号替换为 ' -'”逻辑
            #        然后再循环一次（最多两次）
            base_affil_str_prev = base_affil_str
            base_affil_str = replace_last_comma_with_dash(base_affil_str)

            # 如果替换前后没有变化，说明没有逗号可替换，结束循环
            if base_affil_str == base_affil_str_prev:
                final_mark = mark
                final_affils = new_affils
                break

            attempts += 1

            # 替换后会再次进入 while，重新 split_affil_field + try_fix...

        # 防御：如果 while 正常结束但 final_affils 还没被赋值，就用当前 affils
        if final_affils is None:
            final_affils = split_affil_field(base_affil_str)

        # 统计：是否发生了修改
        original_affils = split_affil_field(row[AFFIL_COL])
        if final_affils != original_affils:
            fixed_count += 1

        if final_mark:
            has_mark_count += 1

        new_affil_str = join_affil_field(final_affils)
        new_affil_col.append(new_affil_str)
        marks.append(final_mark)

        if idx % 500 == 0:
            print(f"  已处理 {idx} / {total_rows} 行...")

    # 覆盖原来的 affiliations 列
    df[AFFIL_COL] = new_affil_col
    # 保留一个 mark 列方便你后面筛查
    df["mark"] = marks

    print(f"总行数: {total_rows}")
    print(f"  自动修改（包括 and 拆分 / 逗号合并）的行数: {fixed_count}")
    print(f"  有 mark 需要关注的行数: {has_mark_count}")

    df.to_csv(OUTPUT_CSV, index=False, encoding=ENCODING)
    print(f"已保存到: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
