from __future__ import annotations
import pandas as pd

from .ror_index import RorMatcher
from .classifier import classify_affiliations_for_row


INPUT_CSV = r"E:\SSRNPaperResearch\data\Biorn\result\Bio_law_clarify11.csv"
OUTPUT_CSV = r"E:\SSRNPaperResearch\data\Biorn\result\Bio_law_ror1234.csv"
ROR_PKL = r"E:\SSRNPaperResearch\data\new_ror_name.pkl"
AFFIL_COL = "affiliations"
ENCODING = "utf-8-sig"


def main() -> None:
    print("初始化 ROR 匹配引擎（倒排索引加速）...")
    ror_matcher = RorMatcher(ROR_PKL)

    print(f"读取 CSV: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, encoding=ENCODING)

    if AFFIL_COL not in df.columns:
        raise ValueError(f"CSV 中找不到列 '{AFFIL_COL}'")

    affil_details = []
    match_confs = []
    english_bgs = []
    affil_ror_ids = []   # ★ 新增：每行所有匹配到的 ROR URL

    for idx, val in df[AFFIL_COL].items():
        affil_str = "" if pd.isna(val) else str(val)

        # 现在 classify_affiliations_for_row 返回 4 个值
        detail, conf, en_bg, ror_ids = classify_affiliations_for_row(
            affil_str,
            ror_matcher,
        )

        affil_details.append(detail)
        match_confs.append(conf)
        english_bgs.append(en_bg)
        affil_ror_ids.append(ror_ids)   # ★ 新增

        if idx % 300 == 0:
            print(f"  已处理 {idx} 行...")

    df["affil_detail"] = affil_details
    df["match_conf"] = match_confs
    df["english_background"] = english_bgs
    df["affil_ror_ids"] = affil_ror_ids   # ★ 新增列

    df.to_csv(OUTPUT_CSV, index=False, encoding=ENCODING)
    print(f"处理完成，保存到: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

