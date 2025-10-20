# src/<你的包>/utils.py
from __future__ import annotations
import asyncio, os, random, re
from typing import List, Set, Optional
from playwright.async_api import Page
from .config import CHALLENGE_KEYWORDS, PAGE_DELAY_RANGE

async def polite_sleep(a: float, b: float):
    await asyncio.sleep(random.uniform(a, b))

def looks_like_challenge(text: str) -> bool:
    low = (text or "").lower()
    return any(k in low for k in CHALLENGE_KEYWORDS)

async def humanize_page(page: Page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
        Object.defineProperty(navigator, 'platform',  { get: () => 'Win32' });
        Object.defineProperty(navigator, 'plugins',   { get: () => [1,2,3,4,5] });
    """)

async def gentle_scroll(page: Page):
    try:
        for _ in range(random.randint(2, 3)):
            await page.mouse.wheel(0, random.randint(250, 600))
            await polite_sleep(0.25, 0.6)
    except Exception:
        pass

async def slight_mouse_move(page: Page):
    try:
        for _ in range(random.randint(1, 3)):
            await page.mouse.move(
                random.randint(50, 1200),
                random.randint(80, 700),
                steps=random.randint(5, 12)
            )
            await polite_sleep(0.15, 0.35)
    except Exception:
        pass

def extract_abstract_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"abstract_id=(\d+)", url)
    return m.group(1) if m else None

async def load_links_on_page(list_page: Page, url: str, selectors: List[str]) -> List[str]:
    await list_page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await slight_mouse_move(list_page)
    await gentle_scroll(list_page)
    await polite_sleep(*PAGE_DELAY_RANGE)
    links: List[str] = []
    for sel in selectors:
        try:
            links = await list_page.eval_on_selector_all(sel, "els => els.map(el => el.href)")
        except:
            links = []
        if links: break
    links = [u for u in links if "papers.cfm?abstract_id=" in u]
    return list(dict.fromkeys(links))

def make_filename(abstract_id: str, page_num: int, ordinal_on_page: int) -> str:
    # "1984_page18_NO.21" 这样的命名
    return f"{abstract_id}_page{page_num}_NO.{ordinal_on_page}"

