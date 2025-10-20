# src/<你的包>/scraping.py
from __future__ import annotations
import os, asyncio
from typing import Tuple
from .config import CHALLENGE_SIZE_BYTES, KEEP_TINY_FILES, ARTICLE_DELAY_RANGE, ARTICLE_TIMEOUT
from .utils import humanize_page, slight_mouse_move, gentle_scroll, polite_sleep, looks_like_challenge

async def fetch_article_text(context, url: str, save_dir: str, file_stem: str) -> Tuple[bool, bool, int]:
    """
    return: (saved_ok, hit_challenge, size_bytes)
    file_stem: 已按你的规则拼好的名字（不含扩展名）
    """
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=ARTICLE_TIMEOUT * 1000)
        await humanize_page(page)
        await slight_mouse_move(page)
        await gentle_scroll(page)
        await polite_sleep(*ARTICLE_DELAY_RANGE)

        body = await page.inner_text("body")

        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{file_stem}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)

        size_bytes = os.path.getsize(path)
        is_tiny = size_bytes <= CHALLENGE_SIZE_BYTES or looks_like_challenge(body)

        if is_tiny:
            if not KEEP_TINY_FILES:
                try: os.remove(path)
                except: pass
            else:
                chall_dir = os.path.join(save_dir, "_challenge")
                os.makedirs(chall_dir, exist_ok=True)
                try: os.replace(path, os.path.join(chall_dir, f"{file_stem}.txt"))
                except: pass
            print(f"🧱 小文件/疑似验证（{size_bytes}B），跳过计数: {url}")
            return (False, True, size_bytes)

        print(f"✅ 保存 {path} ({size_bytes}B) ({url})")
        return (True, False, size_bytes)

    except asyncio.TimeoutError:
        print(f"⚠️ 超时 {ARTICLE_TIMEOUT}s，跳过: {url}")
        return (False, False, 0)
    except Exception as e:
        print(f"❌ 详情异常: {url} -> {e}")
        return (False, False, 0)
    finally:
        await page.close()
