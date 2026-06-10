import os
import logging
from pathlib import Path
from playwright.async_api import Browser, BrowserContext, Page
from config import settings

logger = logging.getLogger("instagram_session")

def get_session_file_path() -> str:
    """
    Returns absolute path to the session storage state file.
    """
    return os.path.abspath(settings.INSTAGRAM_SESSION_PATH)

async def create_instagram_context(browser: Browser, headless: bool = False) -> BrowserContext:
    """
    Creates a new browser context initialized with the saved Instagram session state.
    Configures anti-detection headers, user agents, and evasion scripts.
    """
    session_path = get_session_file_path()
    
    # Anti-bot options
    context_options = {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if os.path.exists(session_path) and os.path.getsize(session_path) > 0:
        logger.info(f"Loading Instagram session from: {session_path}")
        context_options["storage_state"] = session_path
    else:
        logger.warning(f"No valid session state file found at: {session_path}. Context will be unauthenticated.")

    context = await browser.new_context(**context_options)
    
    # Evasion scripts to bypass client-side bot detection
    await context.add_init_script(
        "const newProto = navigator.__proto__; delete newProto.webdriver; navigator.__proto__ = newProto;"
    )
    
    return context

async def is_session_valid(page: Page) -> bool:
    """
    Checks if the loaded browser session is currently authenticated and active on Instagram.
    Navigates to the home page and checks for typical logged-in indicators.
    """
    try:
        logger.info("Verifying Instagram session validity...")
        # Navigate to Instagram home page
        await page.goto("https://www.instagram.com/", wait_until="networkidle", timeout=30000)
        
        # Give a small buffer for page loads
        await page.wait_for_timeout(3000)
        
        # Check current URL
        current_url = page.url
        logger.info(f"Current resting URL: {current_url}")
        
        if "accounts/login" in current_url:
            logger.warning("Session invalid: Redirected to login page.")
            return False
            
        # Check for existence of navigation elements that only appear when logged in:
        # 1. Direct Inbox Messenger link/icon
        # 2. Search navigation button
        # 3. New post navigation button
        selectors = [
            "a[href='/direct/inbox/']", 
            "svg[aria-label='Direct']", 
            "svg[aria-label='Search']",
            "svg[aria-label='New post']"
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                if count > 0:
                    logger.info(f"Session valid: Found logged-in UI element matching '{selector}'")
                    return True
            except Exception:
                continue
                
        # Fallback: check page text for login button
        login_btn = page.locator("button:has-text('Log In')")
        if await login_btn.count() > 0:
            logger.warning("Session invalid: Found Log In button on page.")
            return False
            
        logger.warning("Session validity uncertain: No distinct logged-in or logged-out indicators found.")
        return False
        
    except Exception as e:
        logger.error(f"Error validating Instagram session: {str(e)}")
        return False
