import asyncio, random
from playwright.async_api import async_playwright
from .config import USER_AGENTS, COOKIE_FILE
from .runner import scrape_all_journals_rotating

async def _main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        ua = random.choice(USER_AGENTS)
        vw = 1366; vh = 840
        try:
            context = await browser.new_context(
                storage_state=COOKIE_FILE,
                user_agent=ua,
                locale="en-US",
                viewport={"width": vw, "height": vh},
            )
        except Exception as e:
            print(f"❌ 加载 {COOKIE_FILE} 失败，请重新登录并导出 cookies: {e}")
            await browser.close()
            return

        try:
            await scrape_all_journals_rotating(context)
        except KeyboardInterrupt:
            print("🛑 捕获到中断（Ctrl+C），断点已保存。")
        finally:
            await browser.close()

def run():
    asyncio.run(_main())

if __name__ == "__main__":
    run()
