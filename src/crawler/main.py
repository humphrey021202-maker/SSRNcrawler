import os, random, asyncio
import argparse
from playwright.async_api import async_playwright
from .runner import scrape_journals_index_snapshot
from .config import COOKIE_FILE, USER_AGENTS,RUN_SSRN, RUN_WILEY
from .scraping import snapshot_wiley_v56_issues


async def run_all(context):
    # 可选：提供命令行覆盖（不需要就省略这段 argparse）
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["ssrn", "wiley", "both"], default=None)
    args, _ = parser.parse_known_args()

    do_ssrn, do_wiley = RUN_SSRN, RUN_WILEY
    if args.source == "ssrn":
        do_ssrn, do_wiley = True, False
    elif args.source == "wiley":
        do_ssrn, do_wiley = False, True
    elif args.source == "both":
        do_ssrn, do_wiley = True, True

    if do_wiley:
        print("=== 仅保存 Wiley TOC HTML（V56: Issues 1-5）===")
        await snapshot_wiley_v56_issues(context)

    if do_ssrn:
        print("=== 运行 SSRN 抓取（保持原断点机制）===")
        await scrape_journals_index_snapshot(context)


async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=100,
                                              args=["--disable-blink-features=AutomationControlled"])

            storage_state = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
            ua = random.choice(USER_AGENTS)

            context = await browser.new_context(
                storage_state=storage_state,
                user_agent=ua,
                viewport={"width": 1366, "height": 900},
                java_script_enabled=True,
            )
            await context.add_init_script("""Object.defineProperty(navigator, 'webdriver', {get: () => undefined});""")

            try:
                if RUN_WILEY:
                    print("=== 仅保存 Wiley TOC HTML（V56: Issues 1-5）===")
                    await snapshot_wiley_v56_issues(context)  # 不写断点

                if RUN_SSRN:
                    print("=== 运行 SSRN 抓取（含断点机制）===")
                    await scrape_journals_index_snapshot(context)

                await context.storage_state(path=COOKIE_FILE)
            finally:
                await context.close()
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
