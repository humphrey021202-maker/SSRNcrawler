# src/<你的包>/config.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Set
from pathlib import Path
import os


# 运行开关（可在命令行覆盖）
RUN_SSRN: bool = False
RUN_WILEY: bool = True

# —— 项目根 & data 目录 ——
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# —— 将 cookies / checkpoint 固定到 data/ 下 ——
COOKIE_FILE = str(DATA_DIR / "cookies.json")
CHECKPOINT_FILE = str(DATA_DIR / "resume_checkpoint.json")

CHECKPOINT_EVERY = 1
PERSIST_SEEN_IDS = True

CHALLENGE_SIZE_BYTES = 1024
COOLDOWN_RANGE = (15, 40)      # 建议与 BACKOFF_* 保持一致语义
KEEP_TINY_FILES = True

YEAR_INCLUDE: Set[int] = set()
ENABLE_GLOBAL_DEDUP = True
# 单页命中验证/失败时的重试上限
RETRY_PER_PAGE = 5

# 期刊列表仍可手工配置起始页；end_page 将被忽略（自动到尾页）
JOURNAL_IDS = {
    #"Biochemistry" : 2929808,
    #"Computing_Bio" : 2878323,
    #"Pharmacology":2878529,
    #"Biodiversity":4521845,
    #"Ecology":2878344,
    #"Physiology":2878551,
    #"Bio_Cognitive": 2878603,
    #"Genetics":2878360,
    "Stem_Cell":2878342,
    "Bio_law":2878626,
    "Human_Health":2929907,
    "Bio_Physiology":2878612,
    "Toxicology":2878568,
    "Immunology":4266118,
    "Virology":4266124,
    "Bio_Sustainability":2878646,
    "MicroBiology":4266116,
    "Zoology":2929811,
    "BioTech":2878497,
    "Botany":2878299,
    "Neurobiology":2878517,
    "Parasitology":4266119

}
JOURNAL_PAGE_RANGE: Dict[str, Tuple[int, int]] = {
    #"Biochemistry": (1, 168),
    #"Computing_Bio": (1, 78),
    #"Pharmacology": (1, 70),
    #"Biodiversity": (1, 50),
    #"Ecology": (1, 132),
    #"Physiology":(1,48),
    #"Bio_Cognitive":(1,36),
    #"Genetics": (1,167),
    "Stem_Cell":(1,25),
    "Bio_law":(1,66),
    "Human_Health":(1,200),
    "Bio_Physiology":(1,15),
    "Toxicology":(1,39),
    "Immunology":(1,52),
    "Virology":(1,29),
    "Bio_Sustainability":(1,131),
    "MicroBiology":(1,120),
    "Zoology":(1,38),
    "BioTech":(1,169),
    "Botany":(1,72),
    "NeuroBiology":(1,98),
    "Parasitology":(1,19)
}

JOURNAL_URL_TEMPLATE = (
    "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm"
    "?form_name=journalBrowse&journal_id={jid}&page={page}&sort=0"
)

# 并发：详情串行更稳，避免对抗风控时多开
PARALLEL_CATEGORIES = 1
GLOBAL_DETAIL_CONCURRENCY = 1
DETAIL_TASK_BATCH = 1
PAGE_DELAY_RANGE = (1.2, 2.4)
ARTICLE_DELAY_RANGE = (1.0, 1.6)
ARTICLE_TIMEOUT = 40
START_STAGGER = (0.6, 1.2)

# 反爬退避：一次命中即冷却；最大 40s（按你要求）
BACKOFF_BASE = 20
BACKOFF_MAX = 40                 # ← 由 60 改为 40

MAX_CHALLENGES_PER_CATEGORY = 1  # ← 一次命中就退（不再“轮转”）

CHALLENGE_KEYWORDS = [
    "verify you are human",
    "checking your browser",
    "access denied",
    "temporarily unavailable",
    "验证您是人类",
    "需要检查连接的安全性",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ===== Wiley TOC (Volume 56, Issues 1–5) =====
WILEY_JOURNAL_PREFIX = "https://onlinelibrary.wiley.com"
WILEY_ISSUE_URLS_V56 = [
    # /toc/<issn>/<year>/<volume>/<issue>
    # 注：2025/56/1~5 的 year=2025；若 Wiley 改年号，这里再改就行
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/1",
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/2",
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/3",
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/4",
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/5",
"https://onlinelibrary.wiley.com/toc/15405915/1970/1/6",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/1",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/2",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/3",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/4",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/5",
"https://onlinelibrary.wiley.com/toc/15405915/1971/2/6",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/1",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/2",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/3",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/4",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/5",
"https://onlinelibrary.wiley.com/toc/15405915/1972/3/6",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/1",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/2",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/3",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/4",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/5",
"https://onlinelibrary.wiley.com/toc/15405915/1973/4/6",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/1",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/2",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/3",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/4",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/5",
"https://onlinelibrary.wiley.com/toc/15405915/1974/5/6",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/1",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/2",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/3",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/4",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/5",
"https://onlinelibrary.wiley.com/toc/15405915/1975/6/6",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/1",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/2",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/3",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/4",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/5",
"https://onlinelibrary.wiley.com/toc/15405915/1976/7/6",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/1",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/2",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/3",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/4",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/5",
"https://onlinelibrary.wiley.com/toc/15405915/1977/8/6",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/1",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/2",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/3",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/4",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/5",
"https://onlinelibrary.wiley.com/toc/15405915/1978/9/6",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/1",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/2",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/3",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/4",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/5",
"https://onlinelibrary.wiley.com/toc/15405915/1979/10/6",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/1",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/2",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/3",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/4",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/5",
"https://onlinelibrary.wiley.com/toc/15405915/1980/11/6",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/1",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/2",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/3",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/4",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/5",
"https://onlinelibrary.wiley.com/toc/15405915/1981/12/6",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/1",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/2",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/3",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/4",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/5",
"https://onlinelibrary.wiley.com/toc/15405915/1982/13/6",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/1",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/2",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/3",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/4",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/5",
"https://onlinelibrary.wiley.com/toc/15405915/1983/14/6",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/1",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/2",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/3",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/4",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/5",
"https://onlinelibrary.wiley.com/toc/15405915/1984/15/6",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/1",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/2",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/3",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/4",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/5",
"https://onlinelibrary.wiley.com/toc/15405915/1985/16/6",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/1",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/2",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/3",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/4",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/5",
"https://onlinelibrary.wiley.com/toc/15405915/1986/17/6",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/1",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/2",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/3",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/4",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/5",
"https://onlinelibrary.wiley.com/toc/15405915/1987/18/6",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/1",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/2",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/3",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/4",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/5",
"https://onlinelibrary.wiley.com/toc/15405915/1988/19/6",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/1",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/2",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/3",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/4",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/5",
"https://onlinelibrary.wiley.com/toc/15405915/1989/20/6",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/1",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/2",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/3",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/4",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/5",
"https://onlinelibrary.wiley.com/toc/15405915/1990/21/6",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/1",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/2",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/3",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/4",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/5",
"https://onlinelibrary.wiley.com/toc/15405915/1991/22/6",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/1",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/2",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/3",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/4",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/5",
"https://onlinelibrary.wiley.com/toc/15405915/1992/23/6",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/1",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/2",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/3",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/4",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/5",
"https://onlinelibrary.wiley.com/toc/15405915/1993/24/6",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/1",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/2",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/3",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/4",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/5",
"https://onlinelibrary.wiley.com/toc/15405915/1994/25/6",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/1",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/2",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/3",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/4",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/5",
"https://onlinelibrary.wiley.com/toc/15405915/1995/26/6",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/1",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/2",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/3",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/4",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/5",
"https://onlinelibrary.wiley.com/toc/15405915/1996/27/6",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/1",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/2",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/3",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/4",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/5",
"https://onlinelibrary.wiley.com/toc/15405915/1997/28/6",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/1",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/2",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/3",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/4",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/5",
"https://onlinelibrary.wiley.com/toc/15405915/1998/29/6",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/1",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/2",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/3",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/4",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/5",
"https://onlinelibrary.wiley.com/toc/15405915/1999/30/6",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/1",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/2",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/3",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/4",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/5",
"https://onlinelibrary.wiley.com/toc/15405915/2000/31/6",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/1",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/2",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/3",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/4",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/5",
"https://onlinelibrary.wiley.com/toc/15405915/2001/32/6",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/1",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/2",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/3",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/4",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/5",
"https://onlinelibrary.wiley.com/toc/15405915/2002/33/6",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/1",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/2",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/3",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/4",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/5",
"https://onlinelibrary.wiley.com/toc/15405915/2003/34/6",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/1",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/2",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/3",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/4",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/5",
"https://onlinelibrary.wiley.com/toc/15405915/2004/35/6",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/1",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/2",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/3",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/4",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/5",
"https://onlinelibrary.wiley.com/toc/15405915/2005/36/6",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/1",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/2",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/3",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/4",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/5",
"https://onlinelibrary.wiley.com/toc/15405915/2006/37/6",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/1",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/2",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/3",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/4",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/5",
"https://onlinelibrary.wiley.com/toc/15405915/2007/38/6",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/1",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/2",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/3",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/4",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/5",
"https://onlinelibrary.wiley.com/toc/15405915/2008/39/6",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/1",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/2",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/3",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/4",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/5",
"https://onlinelibrary.wiley.com/toc/15405915/2009/40/6",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/1",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/2",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/3",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/4",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/5",
"https://onlinelibrary.wiley.com/toc/15405915/2010/41/6",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/1",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/2",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/3",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/4",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/5",
"https://onlinelibrary.wiley.com/toc/15405915/2011/42/6",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/1",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/2",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/3",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/4",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/5",
"https://onlinelibrary.wiley.com/toc/15405915/2012/43/6",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/1",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/2",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/3",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/4",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/5",
"https://onlinelibrary.wiley.com/toc/15405915/2013/44/6",

]
WILEY_SAVE_DIRNAME = "wiley_15405915_v56"
@dataclass
class Cursor:
    name: str
    jid: int
    page: int
    end_page: int
    link_idx: int = 0
    links: List[str] = field(default_factory=list)
    save_dir: str = ""
    article_idx: int = 0

