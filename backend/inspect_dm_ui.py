import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Setup paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from playwright_custom.instagram.session import create_instagram_context

async def main():
    print("Launching Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        # Load the synced session state
        context = await create_instagram_context(browser)
        page = await context.new_page()
        
        # We can navigate directly to the thread
        thread_id = "340282366841710301244259481276188036355" # itsellagonzales
        url = f"https://www.instagram.com/direct/t/{thread_id}/"
        print(f"Navigating to thread URL: {url}")
        
        await page.goto(url, wait_until="networkidle")
        print("Page loaded. Waiting 10 seconds for chat content...")
        await page.wait_for_timeout(10000)
        
        # Check title and current URL
        print(f"Current URL: {page.url}")
        print(f"Page Title: {await page.title()}")
        
        # Print some info about the buttons in DOM
        print("Searching for buttons, links or template cards in the chat...")
        buttons = await page.query_selector_all("button")
        print(f"Found {len(buttons)} button elements on the page.")
        for idx, btn in enumerate(buttons):
            text = await btn.inner_text()
            print(f"  Button [{idx}]: '{text.strip()}'")
            
        elements = await page.query_selector_all("a")
        print(f"Found {len(elements)} link elements on the page.")
        for idx, elem in enumerate(elements[:20]):
            text = await elem.inner_text()
            href = await elem.get_attribute("href")
            print(f"  Link [{idx}]: Text='{text.strip()}', Href='{href}'")
            
        # Take a screenshot to visualize
        screenshot_path = project_root / "dm_thread_screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved to: {screenshot_path}")
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
