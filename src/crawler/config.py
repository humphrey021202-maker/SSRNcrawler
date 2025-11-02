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
    #"Emerging Legal Issues in Information Systems eJournal": 4621655,
    "eBusiness & eCommerce eJournal": 1475385,
    "Information Systems Legislation & Regulations eJournal": 2495585,
    "Information Systems & eBusiness Negative Results eJournal": 3045514,
    "Behavioral & Social Methods eJournal": 1475411,
    "Technology & Systems eJournal": 1475394

}
JOURNAL_PAGE_RANGE: Dict[str, Tuple[int, int]] = {
    #"Emerging Legal Issues in Information Systems eJournal": (1, 200),   # 结束页不再使用；仅保留起始页
    "eBusiness & eCommerce eJournal": (1, 79),
    "Information Systems Legislation & Regulations eJournal":(1, 128),
    "Information Systems & eBusiness Negative Results eJournal": (1, 7),
    "Behavioral & Social Methods eJournal": (1,86),
    "Technology & Systems eJournal": (1,62)

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

