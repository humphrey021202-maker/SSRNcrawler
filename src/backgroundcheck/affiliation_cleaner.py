from __future__ import annotations
import re
from typing import List, Dict
from .config import NA_PHRASES

def normalize_space(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "")
    return s.strip()

def remove_and_around_na(text: str) -> str:
    """
    从整条 affiliation 字符串中：
    1. 统一转小写
    2. 对于 N/A 短语（NA_PHRASES 的 key）：
       - 'and phrase' -> 'phrase'
       - 'phrase and' -> 'phrase'
    """
    s = (text or "").lower()

    for phrase in NA_PHRASES.keys():
        # and + phrase
        pattern_before = r"\band\s+" + re.escape(phrase) + r"\b"
        s = re.sub(pattern_before, phrase, s)

        # phrase + and
        pattern_after = r"\b" + re.escape(phrase) + r"\s+and\b"
        s = re.sub(pattern_after, phrase, s)

    s = normalize_space(s)
    return s

def split_affiliations(raw: str) -> List[Dict[str, str]]:
    """
    输入一条 affiliations 原始字符串（可能含 N/A、逗号、分号等）。

    步骤：
      1. lower + 去掉 N/A 附近的 and
      2. 用逗号和分号拆分
      3. 对每个片段判定类别：
         - Independent / NA
         - 或 "candidate"（需要跑 ROR 匹配）

    返回：列表，每个元素是 dict:
      {
        "raw": 片段文本（小写，trim 后）,
        "category": "Independent" / "NA" / "candidate"
      }
    """
    if not isinstance(raw, str):
        return []

    s = remove_and_around_na(raw)

    # 用逗号和分号拆分
    parts = re.split(r"\s*[;,]\s*", s)

    results: List[Dict[str, str]] = []
    for p in parts:
        p_norm = normalize_space(p).strip(" ,;.")
        if not p_norm:
            continue

        cat = NA_PHRASES.get(p_norm.lower())
        if cat is not None:
            results.append({"raw": p_norm, "category": cat})
        else:
            results.append({"raw": p_norm, "category": "candidate"})

    return results
