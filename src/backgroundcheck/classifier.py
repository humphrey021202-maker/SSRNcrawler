from __future__ import annotations
from typing import Tuple
from .affiliation_cleaner import split_affiliations
from .config import ENGLISH_ISO2
from .ror_index import RorMatcher, match_ror_segment


def classify_affiliations_for_row(
    affil_str: str,
    ror_matcher: RorMatcher,
) -> Tuple[str, int, str, str]:
    """
    对一行 affiliations 文本：
      1. 拆分成多个片段（含 Independent / NA / candidate）
      2. 对 candidate 片段做 ROR 匹配：
         - 返回 ISO2 / "unknown"
      3. 综合得到：
         - affil_detail: 例如 "Independent; NA; US; CN; unknown"
         - match_conf:   -1 / 0 / 1
         - english_background: "strong"/"weak"/"unknown"/"Independent"
         - ror_ids_str: 本行匹配到的所有 ROR URL（去重后，用 '; ' 连接）
    """
    segments = split_affiliations(affil_str)

    detail_tokens = []        # 每个片段的分类 token：Independent / NA / ISO2 / unknown
    match_statuses = []       # exact / fuzzy / unknown / independent / na
    ror_ids_for_segments = [] # 与片段一一对应的 ror_id（可能为空字符串）

    for seg in segments:
        cat = seg["category"]
        raw = seg["raw"]

        if cat == "Independent":
            detail_tokens.append("Independent")
            match_statuses.append("independent")
            ror_ids_for_segments.append("")   # Independent 不对应具体机构
        elif cat == "NA":
            detail_tokens.append("N/A")
            match_statuses.append("na")
            ror_ids_for_segments.append("")   # NA 也不对应具体机构
        else:
            # candidate -> ROR 匹配
            country_token, status, ror_id = match_ror_segment(raw, ror_matcher)
            detail_tokens.append(country_token if country_token else "unknown")
            match_statuses.append(status)
            ror_ids_for_segments.append(ror_id or "")

    # 如果这一行啥也没有（非常罕见），默认 unknown
    if not detail_tokens:
        return "", 0, "unknown", ""

    # -------- 计算 match_conf --------
    # 规则：
    # - 只要有 unknown -> -1
    # - 否则，只要有 fuzzy -> 1
    # - 否则（全是 exact / independent / na） -> 0
    if any(st == "unknown" for st in match_statuses):
        match_conf = -1
    elif any(st == "fuzzy" for st in match_statuses):
        match_conf = 1
    else:
        match_conf = 0

    # -------- 计算 english_background --------
    has_strong = any((tok in ENGLISH_ISO2) for tok in detail_tokens)

    all_in_na_ind_unknown = all(
        tok in {"N/A", "Independent", "unknown"} for tok in detail_tokens
    )
    all_independent = all(tok == "Independent" for tok in detail_tokens)

    if has_strong:
        english_bg = "strong"
    elif all_independent:
        english_bg = "Independent"
    elif all_in_na_ind_unknown:
        english_bg = "unknown"
    else:
        english_bg = "weak"

    affil_detail_str = "; ".join(detail_tokens)

    # -------- 汇总本行所有 ROR URL --------
    unique_ror_ids = sorted({rid for rid in ror_ids_for_segments if rid})
    ror_ids_str = "; ".join(unique_ror_ids)

    return affil_detail_str, match_conf, english_bg, ror_ids_str
