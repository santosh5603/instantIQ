import logging
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from ..utils.human_stealth import random_sleep, human_type

logger = logging.getLogger("comment_agent")

async def post_comment(page: Page, reel_url: str, keyword: str) -> bool:
    """
    Navigates to the specified Instagram Reel URL, locates the comment text area,
    types the keyword using human-like keystroke delays, and posts the comment.
    """
    logger.info(f"Navigating to Reel for commenting: {reel_url}")
    
    try:
        await page.goto(reel_url, wait_until="networkidle", timeout=30000)
        # Random sleep to mimic a human scrolling or loading a reel
        await random_sleep(3.0, 6.0)

        # Look for the comment textarea
        # Typical selectors on Instagram desktop web:
        # - textarea[aria-label="Add a comment…"]
        # - textarea[placeholder="Add a comment…"]
        # - form textarea
        textarea_selectors = [
            "textarea[aria-label='Add a comment…']",
            "textarea[aria-label='Add a comment...']",
            "textarea[placeholder='Add a comment…']",
            "textarea[placeholder='Add a comment...']",
            "form textarea",
            "textarea"
        ]
        
        comment_input = None
        for selector in textarea_selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    comment_input = locator.first
                    logger.info(f"Located comment input field using selector: '{selector}'")
                    break
            except Exception:
                continue
                
        if not comment_input:
            logger.error("Failed to locate comment input field on page.")
            return False

        # Click and focus
        await comment_input.scroll_into_view_if_needed()
        await random_sleep(0.5, 1.5)
        await comment_input.click()
        await random_sleep(0.5, 1.0)

        # Type using human stealth
        logger.info(f"Typing keyword: '{keyword}'...")
        await human_type(comment_input, keyword, delay_min_ms=60, delay_max_ms=160)
        
        # Look for "Post" button
        # Typical selectors:
        # - button:has-text('Post')
        # - form button[type="submit"]
        # - div[role="button"]:has-text('Post')
        post_selectors = [
            "button:has-text('Post')",
            "div[role='button']:has-text('Post')",
            "form button[type='submit']",
            "form button"
        ]
        
        post_btn = None
        for selector in post_selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    # Filter out disabled buttons
                    btn = locator.first
                    if not await btn.is_disabled():
                        post_btn = btn
                        logger.info(f"Located active Post button using selector: '{selector}'")
                        break
            except Exception:
                continue

        if not post_btn:
            logger.error("Failed to locate active Post button.")
            return False

        # Pre-post delay (randomized delay to avoid spam detection)
        # settings has COMMENT_DELAY_MIN and COMMENT_DELAY_MAX, usually 10-30s
        # Let's read from settings or default to 5-15s for safety and testability
        from config import settings
        delay_min = getattr(settings, "COMMENT_DELAY_MIN", 5)
        delay_max = getattr(settings, "COMMENT_DELAY_MAX", 15)
        
        logger.info(f"Waiting for pre-post cooldown ({delay_min}-{delay_max} seconds)...")
        await random_sleep(delay_min, delay_max)
        
        # Click post
        logger.info("Clicking Post button...")
        await post_btn.click()
        
        # Post-click verification delay
        await random_sleep(3.0, 5.0)
        logger.info("Comment post attempt completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to post comment on Reel '{reel_url}': {str(e)}")
        return False
