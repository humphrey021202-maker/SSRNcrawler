import csv
import re
import unicodedata
import argparse
import time
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from collections import defaultdict
from functools import lru_cache

# ========= 配置 =========
ENGLISH_COUNTRIES = {"US", "GB", "AU", "CA"}
INSTITUTIONS_COLUMN = "affiliations"
INPUT_ENCODING = "utf-8-sig"
OUTPUT_ENCODING = "utf-8-sig"
FUZZY_THRESHOLD = 92
USE_FUZZY_DEFAULT = True

NO_AFFIL_PHRASE = "affiliation not provided to SSRN"
INDEPENDENT_KEYWORD = "Independent"

# 停用词（用于模糊阶段过滤，避免“university”等过度泛化键）
STOP_TOKENS = {
    "the","of","and","university","college","school","institute","center","centre",
    "hospital","clinic","faculty","lab","laboratory","campus","graduate"
}

# 结果缓存：raw_inst -> Optional[(ror_id, country_code)]
_LOOKUP_MEMO: Dict[str, Optional[Tuple[str, str]]] = {}

# rapidfuzz（可选）
try:
    from rapidfuzz import process, fuzz
    HAS_FUZZ = True
except Exception:
    HAS_FUZZ = False

# ========= 规范化（查询侧 vs 映射侧分离） =========
def _basic_norm(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[‐‒–—−\-/:|,;]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

_PARENS = re.compile(r"[（(].*?[）)]")
_THE = re.compile(r"^\bthe\b\s+")
# 仅用于“查询侧”的尾部裁剪：避免把“University Hospital Bonn”坍缩成“university”
_DEPT_TAIL = re.compile(
    r"\b(department|school|faculty|graduate school|college|institute|center|centre|laboratory|lab|hospital|clinic|campus)\b.*$",
    flags=re.IGNORECASE,
)

@lru_cache(maxsize=100_000)
def query_key_canonical(s: str) -> str:
    """查询侧规范化：会裁掉院系/医院等尾巴，提升召回，但不会影响映射表键。"""
    s = _basic_norm(s)
    s = _PARENS.sub("", s)
    s = _THE.sub("", s)
    s = _DEPT_TAIL.sub("", s)
    s = s.strip()
    return re.sub(r"\s+", " ", s)

@lru_cache(maxsize=100_000)
def map_key_canonical(s: str) -> str:
    """映射表侧规范化：不裁尾巴，保留具体性，避免产生过度泛化键。"""
    s = _basic_norm(s)
    s = _PARENS.sub("", s)
    s = _THE.sub("", s)
    s = s.strip()
    return re.sub(r"\s+", " ", s)

@lru_cache(maxsize=100_000)
def candidate_variants_both_keys(raw: str) -> List[str]:
    """
    为“精确匹配”生成查询侧与映射侧都友好的键候选：
    - 对原文、去括号、分隔符前第一段分别产出
    - 同时生成 query_key_canonical 和 map_key_canonical 两种规范化的候选
    """
    raw = (raw or "").strip()
    cands = set()
    variants = []

    # 原文
    variants.append(raw)

    # 去括号
    no_paren = _PARENS.sub("", raw)
    if no_paren != raw:
        variants.append(no_paren)

    # 分隔符前第一段（raw & no_paren）
    def first_cut(s: str) -> str:
        return re.split(r"[‐‒–—\-:|,;/]", s, maxsplit=1)[0]

    variants.append(first_cut(raw))
    variants.append(first_cut(no_paren))

    # 去前导 the（保险）
    variants = [re.sub(r"^the\s+", "", v.strip(), flags=re.I) for v in variants if v.strip()]

    # 对每个 variant 生成两种键：query_key_canonical / map_key_canonical
    for v in variants:
        qk = query_key_canonical(v)
        mk = map_key_canonical(v)
        if qk:
            cands.add(qk)
        if mk:
            cands.add(mk)

    return [c for c in cands if c]

def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s)

# ========= 加载映射（构建倒排索引） =========
def load_mapping(tsv_path: Path) -> Dict[str, Tuple[str, str]]:
    """
    返回：name_key(映射侧规范化) -> (ror_id, country_code)
    同时在字典中加入特殊键 "__TOKEN_INDEX__" 存放倒排索引，用于缩小模糊候选集。
    """
    name2info: Dict[str, Tuple[str, str]] = {}
    with tsv_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            name_key, rid, cc = parts
            key = map_key_canonical(name_key)  # 重要：映射侧规范化（不裁尾巴）
            if key and rid and (key not in name2info):
                name2info[key] = (rid, cc)

    # 倒排索引：token -> set(keys)
    token_index = defaultdict(set)
    for k in name2info.keys():
        for tok in _tokens(k):
            token_index[tok].add(k)

    # 特殊键存索引
    name2info["__TOKEN_INDEX__"] = token_index  # type: ignore
    return name2info

# ========= 查找：精确（多变体、多规范化） + 模糊（裁剪候选集） =========
def lookup_with_variants(name: str,
                         name2info: Dict[str, Tuple[str, str]],
                         use_fuzzy: bool = USE_FUZZY_DEFAULT,
                         fuzzy_threshold: int = FUZZY_THRESHOLD) -> Optional[Tuple[str, str]]:
    # 结果缓存（基于原始输入去空白）
    memo_key = (name or "").strip()
    if memo_key in _LOOKUP_MEMO:
        return _LOOKUP_MEMO[memo_key]

    # 精确：变体 + 双规范化键
    for cand in candidate_variants_both_keys(name or ""):
        if cand in name2info:
            _LOOKUP_MEMO[memo_key] = name2info[cand]
            return _LOOKUP_MEMO[memo_key]

    # 模糊（可选）：只在“有词交集”的候选键里找，并设置 score_cutoff 早停
    if use_fuzzy and HAS_FUZZ and name2info:
        q = query_key_canonical(name or "")
        if 4 <= len(q) <= 128:
            token_index = name2info.get("__TOKEN_INDEX__")  # type: ignore
            if token_index:
                qtoks_all = set(_tokens(q))
                qtoks = {t for t in qtoks_all if t not in STOP_TOKENS}

                # 收集候选：按（所有词）拿候选，再用“去停用词后的交集>=1”过滤
                cands = set()
                for t in qtoks_all:
                    vals = token_index.get(t)  # 可能是 set / list / None
                    if vals:
                        cands.update(vals)

                filtered = []
                for k in cands:
                    ktoks_all = set(_tokens(k))
                    ktoks = {t for t in ktoks_all if t not in STOP_TOKENS}
                    # 过滤掉极短候选（避免“university”这类键）
                    if len(ktoks_all) <= 1:
                        continue
                    # 要求至少1个非停用词共词
                    if len(qtoks & ktoks) >= 1:
                        filtered.append(k)

                # ★ 默认候选时，排除特殊键；并在末尾统一检查是否为空
                all_keys = [k for k in name2info.keys() if not (isinstance(k, str) and k.startswith("__"))]
                search_space = filtered if filtered else (list(cands) if cands else all_keys)
            else:
                # ★ 无倒排索引时也排除特殊键
                search_space = [k for k in name2info.keys() if not (isinstance(k, str) and k.startswith("__"))]

            # ★ 候选可能为空：直接返回 None
            if not search_space:
                _LOOKUP_MEMO[memo_key] = None
                return None

            # ★ 安全解包：extractOne 可能返回 None
            res = process.extractOne(
                q,
                search_space,
                scorer=fuzz.token_set_ratio,  # 如需更保守可换 token_sort_ratio
                score_cutoff=fuzzy_threshold,
                processor=None  # 我们已经做了规范化
            )
            if res is None:
                _LOOKUP_MEMO[memo_key] = None
                return None

            key = res[0]  # 兼容 v2/v3 的写法
            _LOOKUP_MEMO[memo_key] = name2info[key]
            return _LOOKUP_MEMO[memo_key]

    _LOOKUP_MEMO[memo_key] = None
    return None


# ========= 单元格判定 =========
def judge_institutions_cell(institutions_cell: str,
                            name2info: Dict[str, Tuple[str, str]],
                            english_countries=ENGLISH_COUNTRIES,
                            use_fuzzy: bool = USE_FUZZY_DEFAULT,
                            fuzzy_threshold: int = FUZZY_THRESHOLD):
    raw_full = (institutions_cell or "").strip()
    if not raw_full:
        return ("unknown", [], [], [], "none", 0)

    # 整格等于 “affiliation not provided to SSRN” → unknown（保持不变）
    if _basic_norm(raw_full) == _basic_norm(NO_AFFIL_PHRASE):
        return ("unknown", [], [], [], "none", 0)

    # 拆分多机构（分号）
    inst_raw_list = [x.strip() for x in raw_full.split(";") if x.strip()]

    matched_countries: List[str] = []
    matched_ids: List[str] = []
    unmatched: List[str] = []

    for inst in inst_raw_list:
        # --- NEW: 对于独立研究者，作为一个“命中项”写入国家序列 ---
        if inst.strip().lower() == INDEPENDENT_KEYWORD.lower() or \
           inst.strip().lower() == "independent researcher":
            matched_countries.append("Independent")
            # 不追加 ROR ID；也不计入 unmatched
            continue

        # 其他机构仍旧走映射/模糊匹配
        info = lookup_with_variants(inst, name2info, use_fuzzy=use_fuzzy, fuzzy_threshold=fuzzy_threshold)
        if info:
            rid, cc = info
            matched_ids.append(rid)
            matched_countries.append(cc or "")
        else:
            unmatched.append(inst)

    # —— 整体标签判定（保持不变；Independent 不影响 strong/weak/unknown）——
    # 注意：如果整行只有 "Independent"/"Independent researcher" 而无其他命中，
    # 则 matched_ids 为空、没有英语国家 → 按原逻辑为 "unknown"
    if matched_countries and all((c or "").strip().lower() == "independent" for c in matched_countries):
        label = "independent"
    else:
        if not inst_raw_list:
            label = "unknown"
        elif any(cc in english_countries for cc in matched_countries):
            label = "strong"
        elif len(matched_ids) == 0:
            label = "unknown"
        else:
            label = "weak"

    # match_status 仅按“映射命中数”评估（Independent 不计入）
    mcount = len(matched_ids)
    if mcount == 0:
        mstatus = "none"
    elif mcount == len([x for x in inst_raw_list if x.strip().lower() not in {"independent", "independent researcher"}]):
        mstatus = "full"
    else:
        mstatus = "partial"

    return (label, matched_countries, matched_ids, unmatched, mstatus, mcount)


# ========= 进度工具 =========
def precount_rows(csv_path: Path, encoding: str, has_header: bool = True) -> int:
    cnt = 0
    with csv_path.open("r", encoding=encoding, newline="") as f:
        for _ in f:
            cnt += 1
    return max(0, cnt - (1 if has_header else 0))

# ========= 主程序 =========
def main():
    ap = argparse.ArgumentParser(description="Judge English background with caching, pruned fuzzy, and split canonicalization for mapping/query.")
    ap.add_argument("-i", "--input", required=True, help="Path to papers CSV (must contain affiliations column unless --institutions-col is set).")
    ap.add_argument("-m", "--mapping", default="ror_name_country.tsv", help="Normalized mapping TSV (name_key\\tror_id\\tcountry_code).")
    ap.add_argument("-o", "--output", default=None, help="Output CSV path (default: <input>_with_English_bg.csv).")
    ap.add_argument("--encoding-in", default=INPUT_ENCODING, help=f"Input CSV encoding (default: {INPUT_ENCODING}).")
    ap.add_argument("--encoding-out", default=OUTPUT_ENCODING, help=f"Output CSV encoding (default: {OUTPUT_ENCODING}).")
    ap.add_argument("--institutions-col", default=INSTITUTIONS_COLUMN, help=f"Institutions column name (default: {INSTITUTIONS_COLUMN}).")
    ap.add_argument("--no-fuzzy", action="store_true", help="Disable fuzzy fallback even if rapidfuzz is installed.")
    ap.add_argument("--fuzzy-threshold", type=int, default=FUZZY_THRESHOLD, help=f"Fuzzy score threshold (default: {FUZZY_THRESHOLD}).")
    ap.add_argument("--progress-every", type=int, default=1000, help="Print speed/progress every N rows (default: 1000).")
    ap.add_argument("--precount", action="store_true", help="Pre-count total rows to show ETA (slightly slower startup).")
    args = ap.parse_args()

    input_path = Path(args.input)
    mapping_path = Path(args.mapping)
    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_with_English_bg.csv")

    if not input_path.exists():
        raise SystemExit(f"❌ Input CSV not found: {input_path}")
    if not mapping_path.exists():
        raise SystemExit(f"❌ Mapping TSV not found: {mapping_path}")

    print(f"📥 Loading mapping: {mapping_path}")
    name2info = load_mapping(mapping_path)
    print(f"✅ Mapping loaded: {len([k for k in name2info.keys() if not k.startswith('__')]):,} keys")

    use_fuzzy = (not args.no_fuzzy) and HAS_FUZZ
    if (not HAS_FUZZ) and (not args.no_fuzzy):
        print("ℹ️ rapidfuzz not installed; running without fuzzy fallback.\n    Install with: pip install rapidfuzz")

    total_rows = None
    if args.precount:
        print("🔎 Pre-counting total rows for ETA…")
        total_rows = precount_rows(input_path, args.encoding_in)
        print(f"🧮 Total data rows (excluding header): {total_rows:,}")

    with input_path.open("r", encoding=args.encoding_in, newline="") as fin, \
         output_path.open("w", encoding=args.encoding_out, newline="") as fout:
        reader = csv.DictReader(fin)
        fieldnames = list(reader.fieldnames or [])
        if args.institutions_col not in fieldnames:
            raise SystemExit(f"❌ Column not found in input CSV: {args.institutions_col}")

        # 附加输出列
        for col in ("english_background", "matched_countries", "matched_ror_ids",
                    "unmatched_institutions", "match_status", "match_count"):
            if col not in fieldnames:
                fieldnames.append(col)

        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        rows = 0
        t0 = time.time()
        last_t = t0
        last_rows = 0

        for row in reader:
            rows += 1
            label, countries, rids, unmatched, mstatus, mcount = judge_institutions_cell(
                row.get(args.institutions_col, ""),
                name2info,
                english_countries=ENGLISH_COUNTRIES,
                use_fuzzy=use_fuzzy,
                fuzzy_threshold=args.fuzzy_threshold
            )
            row["english_background"] = label
            row["matched_countries"] = ",".join([c for c in countries if c])
            row["matched_ror_ids"] = ",".join(rids)
            row["unmatched_institutions"] = ";".join(unmatched)
            row["match_status"] = mstatus
            row["match_count"] = str(mcount)
            writer.writerow(row)

            # 进度与速度
            if args.progress_every > 0 and (rows % args.progress_every == 0):
                now = time.time()
                elapsed = now - t0
                batch_elapsed = now - last_t
                avg_speed = rows / elapsed if elapsed > 0 else 0.0
                batch_rows = rows - last_rows
                batch_speed = batch_rows / batch_elapsed if batch_elapsed > 0 else 0.0
                eta_str = ""
                if total_rows is not None and avg_speed > 0:
                    remaining = max(0, total_rows - rows)
                    eta_sec = remaining / avg_speed
                    eta_str = f" | ETA ~ {eta_sec/60:.1f} min"
                print(f"⏱️ {rows:,} rows | avg {avg_speed:.2f} rows/s | last {batch_speed:.2f} rows/s{eta_str}")
                last_t = now
                last_rows = rows

    t1 = time.time()
    elapsed = t1 - t0
    avg_speed = (rows / elapsed) if elapsed > 0 else 0.0
    print(f"✅ Done. Processed {rows:,} rows in {elapsed:.2f}s (avg {avg_speed:.2f} rows/s).")
    print(f"📄 Output: {output_path}")

if __name__ == "__main__":
    import sys
    sys.argv = [
        sys.argv[0],
        "-i", "E:/SSRNPaperResearch/data/isn/result/TechnologySystemseJournal.csv",
        "-m", "E:/SSRNPaperResearch/data/ror_name_country_norm.tsv",
        "--progress-every", "500",
        "--precount"
    ]
    main()