from __future__ import annotations
import re
import pickle
from typing import Dict, List, Set, Tuple, Optional
from rapidfuzz import process, fuzz

TOKEN_SPLIT_RE = re.compile(r"[^\w']+")

DEFAULT_STOPWORDS = {
    "university", "college", "institute", "institut", "school",
    "department", "center", "centre", "faculty",
    "of", "the", "for", "in", "de", "di",
}

def tokenize(text: str) -> List[str]:
    """简单 token 化：按非字母数字分割，并转小写。"""
    if not isinstance(text, str):
        return []
    tokens = [t.lower() for t in TOKEN_SPLIT_RE.split(text) if t]
    return tokens

class RorMatcher:
    """
    ROR 加速匹配引擎：
      - 从 ror_slim.pkl 加载机构：
        每条记录形如：
           {"id": ..., "country_code": "AU", "names": ["RMIT", "RMIT University", ...]}
      - 构建：
           * name_to_country: 精确匹配用（name_lower -> country_code）
           * all_names: 所有名称（小写字符串列表）
           * token_index: token -> set(name_lower)，倒排表

    match(segment):
      1. 精确匹配：O(1)
      2. 根据 tokens 从倒排表取候选名称集合
      3. 在候选上用 rapidfuzz fuzzy 匹配
    """

    def __init__(
        self,
        pkl_path: str,
        stopwords: Optional[Set[str]] = None,
        min_token_len: int = 3,
    ) -> None:
        self.pkl_path = pkl_path
        self.stopwords: Set[str] = stopwords or DEFAULT_STOPWORDS
        self.min_token_len = min_token_len

        self.all_names: List[str] = []                 # 所有名称（小写）
        self.name_to_country: Dict[str, Optional[str]] = {}  # name_lower -> country_code
        self.token_index: Dict[str, Set[str]] = {}     # token -> set(name_lower)
        self.name_to_rorid: Dict[str, Optional[str]] = {}    # ★ 新增：name_lower -> ror_id (URL)

        self._load_and_build()

    def _load_and_build(self) -> None:
        print(f"从 {self.pkl_path} 加载 ROR slim 数据 ...")
        with open(self.pkl_path, "rb") as f:
            slim_orgs = pickle.load(f)

        print(f"  共有 {len(slim_orgs)} 个机构记录，开始构建索引...")

        for org in slim_orgs:
            country = org.get("country_code")
            ror_id = org.get("id")  # 形如 "https://ror.org/04ttjf776"
            names = org.get("names") or []
            for name in names:
                name_l = name.lower()
                self.all_names.append(name_l)

                # 精确匹配字典
                if name_l not in self.name_to_country:
                    self.name_to_country[name_l] = country

                # ★ 新增：名字 -> ror_id（第一次出现的为主）
                if name_l not in self.name_to_rorid:
                    self.name_to_rorid[name_l] = ror_id

                # 为倒排索引做 token 化
                toks = tokenize(name_l)
                for tok in toks:
                    if len(tok) < self.min_token_len:
                        continue
                    if tok in self.stopwords:
                        continue
                    self.token_index.setdefault(tok, set()).add(name_l)

        print(f"  名称总数: {len(self.all_names)}")
        print(f"  倒排表 token 数量: {len(self.token_index)}")
        print("  ROR 索引构建完成。")

    def _candidate_names_from_segment(self, seg: str) -> List[str]:
        """根据片段 tokens，从倒排表中取出候选名称（字符串）。"""
        toks = tokenize(seg)
        cand_set: Set[str] = set()

        for tok in toks:
            if len(tok) < self.min_token_len:
                continue
            if tok in self.stopwords:
                continue
            names = self.token_index.get(tok)
            if names:
                cand_set.update(names)

        return list(cand_set)

    def match(self, seg: str, threshold: float = 95.0) -> Tuple[str, str, float, str]:
        """
        对一个机构片段进行匹配：
        返回: (country_code_or_unknown, match_status, score, ror_id_or_empty)
            - country_code_or_unknown: "US" / "CN" / "unknown"
            - match_status: "exact" / "fuzzy" / "unknown"
            - score: fuzzy 匹配得分（0-100），精确匹配时为 100
            - ror_id_or_empty: 例如 "https://ror.org/04ttjf776" 或 ""
        """
        if not isinstance(seg, str):
            return "unknown", "unknown", 0.0, ""

        q = seg.strip().lower()
        if not q:
            return "unknown", "unknown", 0.0, ""

        # 1. 精确匹配
        if q in self.name_to_country:
            country = self.name_to_country.get(q)
            ror_id = self.name_to_rorid.get(q) or ""
            if country:
                return country.upper(), "exact", 100.0, ror_id
            else:
                return "unknown", "unknown", 100.0, ror_id

        # 2. 通过 tokens 找候选名称（字符串）
        cand_names = self._candidate_names_from_segment(q)
        if not cand_names:
            return "unknown", "unknown", 0.0, ""

        # 3. 仅在候选名称上做 fuzzy 匹配
        best_name, score, _ = process.extractOne(
            q,
            cand_names,
            scorer=fuzz.token_set_ratio,
        )

        if score >= threshold:
            country = self.name_to_country.get(best_name)
            ror_id = self.name_to_rorid.get(best_name) or ""
            if country:
                return country.upper(), "fuzzy", float(score), ror_id
            else:
                return "unknown", "unknown", float(score), ror_id
        else:
            return "unknown", "unknown", float(score), ""


def match_ror_segment(seg: str, ror_matcher: "RorMatcher", threshold: float = 95.0):
    """
    对外简化的匹配接口（供 classifier 调用）。
    返回: (country_token, status, ror_id)
      - country_token: ISO2 or "unknown"
      - status: "exact" / "fuzzy" / "unknown"
      - ror_id: 识别到的机构 ROR URL；若无则为 ""
    """
    country, status, score, ror_id = ror_matcher.match(seg, threshold=threshold)
    return country if country else "unknown", status, ror_id or ""

