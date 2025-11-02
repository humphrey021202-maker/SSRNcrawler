import os, random, asyncio
from playwright.async_api import async_playwright
from .runner import scrape_journals_index_snapshot
from .config import COOKIE_FILE, USER_AGENTS

async def main():
    async with async_playwright() as p:
        # 建议先 headless=False 跑一轮“培养”cookie；OK后再改 True
        browser = await p.chromium.launch(headless=False, slow_mo=100,
                                          args=["--disable-blink-features=AutomationControlled"])

        storage_state = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
        ua = random.choice(USER_AGENTS)

        context = await browser.new_context(
            storage_state=storage_state,
            user_agent=ua,
            locale="en-US",
            timezone_id="America/New_York",   # 任一常见时区即可
            viewport={"width": 1366, "height": 768},
            device_scale_factor=1.0,
            java_script_enabled=True,
        )
        # 降低 webdriver 暴露
        await context.add_init_script("""Object.defineProperty(navigator, 'webdriver', {get: () => undefined});""")

        try:
            await scrape_journals_index_snapshot(context)
            await context.storage_state(path=COOKIE_FILE)
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
