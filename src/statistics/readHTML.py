from __future__ import annotations
import sys
import re
from pathlib import Path
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
import csv
import unicodedata

# Optional encoding detection (if installed)
try:
    from charset_normalizer import from_bytes as detect_from_bytes
except Exception:
    detect_from_bytes = None

DELIM = ';'  # 英文分号

AND_RE = re.compile(r"\band\b", re.I)
# split by commas or 'and' with surrounding spaces
SPLIT_RE = re.compile(r"\s*,\s*|\s+and\s+", re.I)

ABSTRACT_ID_RE = re.compile(r"abstract_id=(\d+)")


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def read_html_text(path: Path) -> str:
    """Read HTML bytes with robust decoding.
    Priority: UTF-8 -> charset_normalizer guess -> latin-1 (replace).
    Then normalize to NFC for diacritics (e.g., 'ń').
    """
    raw = path.read_bytes()
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        if detect_from_bytes is not None:
            best = detect_from_bytes(raw).best()
            if best is not None:
                txt = str(best)
            else:
                txt = raw.decode('latin-1', errors='replace')
        else:
            txt = raw.decode('latin-1', errors='replace')
    return nfc(txt)


def find_abstract_id(href: str) -> Optional[str]:
    if not href:
        return None
    m = ABSTRACT_ID_RE.search(href)
    return m.group(1) if m else None


def simple_split_by_commas_and_and(text: str, n: int) -> Tuple[List[str], bool]:
    """Most common case: n authors -> (n-2) commas + 1 'and'.
    If matches, split by commas and 'and'. Return (parts, needs_review).
    """
    t = normalize_space(text)
    comma_cnt = t.count(',')
    and_cnt = len(AND_RE.findall(t))

    if n <= 1:
        return ([t] if t else []), False

    if and_cnt == 1 and comma_cnt == (n - 2):
        parts = [normalize_space(p) for p in SPLIT_RE.split(t) if normalize_space(p)]
        if len(parts) == n:
            return parts, False
        return parts if parts else [t], True
    return [t], True


def try_fix_multiple_and(text: str, n: int) -> Tuple[List[str], bool]:
    """If more than one 'and' exists:
    - Look at the tail after the last comma; if that tail has exactly one 'and',
      split whole text by commas and 'and'. Otherwise, keep as-is.
    """
    t = normalize_space(text)
    if len(AND_RE.findall(t)) <= 1:
        return [t], True

    last_comma = t.rfind(',')
    if last_comma == -1:
        return [t], True

    tail = t[last_comma + 1 :]
    if len(AND_RE.findall(tail)) == 1:
        parts = [normalize_space(p) for p in SPLIT_RE.split(t) if normalize_space(p)]
        if len(parts) == n:
            return parts, False
        return parts if parts else [t], True
    return [t], True


def try_keep_universities_only(text: str, n: int) -> Tuple[List[str], bool]:
    """When there are many commas inside affiliation names, keep only segments
    that contain 'university'. If exactly n segments remain, accept; else mark review.
    """
    t = normalize_space(text)
    tokens = [normalize_space(p) for p in SPLIT_RE.split(t) if normalize_space(p)]
    uni_tokens = [p for p in tokens if 'university' in p.lower()]
    if len(uni_tokens) == n and n > 0:
        return uni_tokens, False
    return [t], True


def split_affiliations(raw_text: str, n_authors: int) -> Tuple[List[str], int]:
    """Apply the rule set to split affiliations text.
    Returns (affil_list, needs_review[0/1]).
    """
    t = normalize_space(raw_text)
    if not t:
        return [], 1 if n_authors > 0 else 0

    # try common case
    parts, bad = simple_split_by_commas_and_and(t, n_authors)
    if not bad:
        return parts, 0

    # multiple 'and' fix
    parts2, bad2 = try_fix_multiple_and(t, n_authors)
    if not bad2 and parts2 != [t]:
        return parts2, 0

    # many commas -> keep only 'university' segments
    parts3, bad3 = try_keep_universities_only(t, n_authors)
    if not bad3 and parts3 != [t]:
        return parts3, 0

    return [t], 1


def parse_one_list_html(path: Path) -> List[dict]:
    """Parse multiple paper records from one list_XXXXX.html file."""
    html = read_html_text(path)
    soup = BeautifulSoup(html, 'lxml')

    out = []
    for paper in soup.select('div.paper'):
        # title & id
        title_tag = paper.select_one('.paper-info .title a, .title a')
        title = normalize_space(title_tag.get_text()) if title_tag else ''
        href = title_tag['href'] if (title_tag and title_tag.has_attr('href')) else ''
        abstract_id = find_abstract_id(href) or ''

        # posted date
        posted_date = ''
        for sp in paper.select('.stats span'):
            txt = sp.get_text(strip=True)
            if txt.lower().startswith('posted'):
                posted_date = normalize_space(txt)
                break

        # authors
        authors = [normalize_space(nfc(a.get_text())) for a in paper.select('.authors a')]

        # affiliations raw
        aff_raw_tag = paper.select_one('.affiliations')
        aff_raw = normalize_space(nfc(aff_raw_tag.get_text())) if aff_raw_tag else ''

        aff_list, needs = split_affiliations(aff_raw, len(authors))

        out.append({
            'abstract_id': abstract_id,
            'title': title,
            'posted': posted_date,
            'authors': DELIM.join(authors) if authors else '',
            'affiliations': DELIM.join(aff_list) if aff_list else '',
            'affil_needs_review': needs,
            'source_file': str(path.name),
        })
    return out


def main(input_dir: str) -> Path:
    root = Path(input_dir).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    # output: <input_dir>/../result/<foldername>.csv
    result_dir = root.parent / 'result'
    result_dir.mkdir(parents=True, exist_ok=True)
    out_csv = result_dir / f"{root.name}.csv"

    rows: List[dict] = []
    for p in sorted(root.glob('*.html')):
        rows.extend(parse_one_list_html(p))

    # write CSV with BOM for Excel
    fieldnames = ['abstract_id', 'title', 'posted', 'authors', 'affiliations', 'affil_needs_review', 'source_file']
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: nfc(str(v)) if isinstance(v, str) else v for k, v in r.items()})

    return out_csv


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python parse_ssrn_dir_v2.py <folder_with_html_files>')
        sys.exit(1)
    output = main(sys.argv[1])
    print(f"✅ Done. CSV saved to: {output}")

