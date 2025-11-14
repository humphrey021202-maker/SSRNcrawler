import os
from typing import Tuple
from playwright.async_api import BrowserContext, TimeoutError,  Page
from pathlib import Path
from .utils import polite_sleep
from .config import DATA_DIR, WILEY_ISSUE_URLS_V56, WILEY_SAVE_DIRNAME


RESULT_SELECTOR = 'a[href*="papers.cfm?abstract_id="]'  # 目录中每条论文都有
CHALLENGE_SIZE_BYTES = 1024  # 你已有的阈值，必要时调低到 512 看看

def _ensure_dirs(path: str):
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "_challenge"), exist_ok=True)

async def fetch_list_page_text(
    context: BrowserContext,
    url: str,
    save_dir: str,
    file_stem: str,   # 例如 "page_00045"
) -> Tuple[bool, bool, int]:
    """
    抓目录页：
      - 等 RESULT_SELECTOR 出现（最长 20s）
      - 成功→保存完整 HTML 到 save_dir/file_stem.html
      - 失败/挑战→保存完整 HTML 到 save_dir/_challenge/file_stem.html
    返回: (saved_normal, hit_challenge, size_bytes)
    """
    _ensure_dirs(save_dir)
    chal_dir = os.path.join(save_dir, "_challenge")

    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)

        # 给点“人类停顿”
        await page.wait_for_timeout(500)

        # 可选：滚动一下，触发可能的惰性加载
        await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight/2); }""")
        await page.wait_for_timeout(300)
        await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
        await page.wait_for_timeout(300)

        # 等结果元素出现（若 20s 内没出现，多半被降级/要登录/被风控）
        try:
            await page.wait_for_selector(RESULT_SELECTOR, state="visible", timeout=20_000)
        except TimeoutError:
            html = await page.content()
            size_bytes = len(html.encode("utf-8", errors="ignore"))
            out = os.path.join(chal_dir, f"{file_stem}.html")
            with open(out, "w", encoding="utf-8", newline="") as f:
                f.write(html)
            return (False, True, size_bytes)

        # 正常：保存完整 HTML
        html = await page.content()
        size_bytes = len(html.encode("utf-8", errors="ignore"))

        # 过小仍按“挑战/降级”归档
        if size_bytes <= CHALLENGE_SIZE_BYTES:
            out = os.path.join(chal_dir, f"{file_stem}.html")
            with open(out, "w", encoding="utf-8", newline="") as f:
                f.write(html)
            return (False, True, size_bytes)

        out = os.path.join(save_dir, f"{file_stem}.html")
        with open(out, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        return (True, False, size_bytes)

    finally:
        try:
            await page.close()
        except Exception:
            pass
def _safe_filename(url: str) -> str:
    # 生成可作文件名的短字符串（按你项目习惯可改）
    name = url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_")
    return (name[:200] if len(name) > 200 else name) + ".html"

async def snapshot_wiley_v56_issues(context: BrowserContext) -> None:
    """
    只保存 Wiley Volume 56，Issues 1-5 的 TOC 整页 HTML。
    不解析、不落断点。
    输出目录：data/<WILEY_SAVE_DIRNAME>/
    文件名：按 URL 生成的 .html
    """
    save_dir = Path(DATA_DIR) / WILEY_SAVE_DIRNAME
    save_dir.mkdir(parents=True, exist_ok=True)

    page: Page = await context.new_page()
    try:
        for idx, issue_url in enumerate(WILEY_ISSUE_URLS_V56, start=1):
            print(f"[Wiley] ({idx}/{len(WILEY_ISSUE_URLS_V56)}) {issue_url}")
            await page.goto(issue_url, wait_until="domcontentloaded", timeout=45_000)
            await polite_sleep(0.2, 0.6)  # 轻微节流

            html = await page.content()
            out_path = save_dir / _safe_filename(issue_url)
            out_path.write_text(html, encoding="utf-8")
            print(f"  ↳ 保存 {out_path}")
    finally:
        try:
            await page.close()
        except Exception:
            pass