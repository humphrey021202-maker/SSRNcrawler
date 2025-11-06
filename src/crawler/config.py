# src/<你的包>/config.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Set
from pathlib import Path
import os

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

