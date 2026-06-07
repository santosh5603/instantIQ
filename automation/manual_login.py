import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load root or local .env
load_dotenv()
load_dotenv(Path(__file__).parent / ".env")

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "reelise_collector")
INSTAGRAM_SESSION_PATH = os.getenv("INSTAGRAM_SESSION_PATH", "session/instagram_session.json")

async def run_manual_login():
    print("=" * 60)
    print("REELISE: INSTAGRAM MANUAL LOGIN HELPER")
    print("=" * 60)
    print("This utility will open a visible Chromium browser window to allow you")
    print("to login manually into your Instagram Collector account.")
    print("This avoids repeated bot-like logins and handles 2FA/MFA seamlessly.")
    print(f"Session path destination: {os.path.abspath(INSTAGRAM_SESSION_PATH)}")
    print("=" * 60)
    
    # Ensure session directory exists
    session_dir = os.path.dirname(INSTAGRAM_SESSION_PATH)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)
        
    async with async_playwright() as p:
        # Launch non-headless browser with visible viewport
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # Configure context
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Add default webdriver evasion script
        await context.add_init_script(
            "const newProto = navigator.__proto__; delete newProto.webdriver; navigator.__proto__ = newProto;"
        )
        
        page = await context.new_page()
        print("Opening Instagram login page...")
        await page.goto("https://www.instagram.com/accounts/login/")
        
        print("\nACTION REQUIRED:")
        print("1. Log in manually in the browser window.")
        print("2. Enter any 2FA code if prompted.")
        print("3. Verify you have arrived at the Instagram feed / homepage.")
        print("4. ONCE LOGGED IN SUCCESSFULLY, return to this terminal and press ENTER.")
        
        # Wait for terminal user confirmation
        input("\nPress ENTER here once you are logged in and resting on the home feed...")
        
        print("Saving session state to storage...")
        state = await context.storage_state(path=INSTAGRAM_SESSION_PATH)
        print(f"SUCCESS: Session saved successfully to '{INSTAGRAM_SESSION_PATH}'!")
        
        # Validate that file is written and not empty
        if os.path.exists(INSTAGRAM_SESSION_PATH) and os.path.getsize(INSTAGRAM_SESSION_PATH) > 0:
            print("File verification: OK")
        else:
            print("ERROR: Session file is empty or was not created.")
            
        print("Closing browser...")
        await context.close()
        await browser.close()
        
    print("Finished.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_manual_login())
