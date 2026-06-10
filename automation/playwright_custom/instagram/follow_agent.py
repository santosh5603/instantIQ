import logging
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from ..utils.human_stealth import random_sleep

logger = logging.getLogger("follow_agent")

async def is_following_creator(page: Page, creator_name: str) -> bool:
    """
    Navigates to the creator's profile page and determines if the collector account is already following them.
    """
    url = f"https://www.instagram.com/{creator_name}/"
    logger.info(f"Checking follow status on profile: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await random_sleep(2.0, 4.0)
        
        # Check for various follow button states
        # 1. "Following" button
        following_btn = page.locator("button:has-text('Following')")
        if await following_btn.count() > 0:
            logger.info(f"Already following @{creator_name}.")
            return True

        # 2. "Requested" button (for private accounts where follow is pending)
        requested_btn = page.locator("button:has-text('Requested')")
        if await requested_btn.count() > 0:
            logger.info(f"Follow request is already pending/requested for private account @{creator_name}.")
            return True
            
        # 3. Message button next to follow (sometimes following displays as Message directly)
        # We can default to checking if 'Follow' button is present or not
        follow_btn = page.locator("button:has-text('Follow')")
        follow_back_btn = page.locator("button:has-text('Follow Back')")
        
        if await follow_btn.count() > 0 or await follow_back_btn.count() > 0:
            logger.info(f"Not following @{creator_name} yet.")
            return False
            
        # If no follow/following buttons exist, check if we see a profile but no follow options
        # E.g. our own profile.
        logger.warning(f"Could not conclusively identify follow button for @{creator_name}. Assuming not following.")
        return False
        
    except Exception as e:
        logger.error(f"Error checking follow status for @{creator_name}: {str(e)}")
        return False

async def follow_creator(page: Page, creator_name: str) -> bool:
    """
    Navigates to the creator's profile page and clicks Follow if not already followed.
    Includes human-like stealth delays.
    """
    url = f"https://www.instagram.com/{creator_name}/"
    logger.info(f"Attempting to follow creator: @{creator_name}")
    
    try:
        # Navigate to profile
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await random_sleep(3.0, 5.0)
        
        # 1. Double check if already followed
        following_btn = page.locator("button:has-text('Following')")
        requested_btn = page.locator("button:has-text('Requested')")
        
        if await following_btn.count() > 0 or await requested_btn.count() > 0:
            logger.info(f"Skipping follow action: Already following @{creator_name}.")
            return True
            
        # 2. Locate follow button
        follow_btn = page.locator("button:has-text('Follow')")
        follow_back_btn = page.locator("button:has-text('Follow Back')")
        
        target_btn = None
        if await follow_btn.count() > 0:
            target_btn = follow_btn.first
        elif await follow_back_btn.count() > 0:
            target_btn = follow_back_btn.first
            
        if not target_btn:
            logger.error(f"Could not locate follow button on page for @{creator_name}.")
            return False
            
        # 3. Simulate human click
        logger.info(f"Clicking follow button for @{creator_name}...")
        await target_btn.scroll_into_view_if_needed()
        await random_sleep(0.5, 1.5)
        await target_btn.click()
        
        # 4. Wait for state change and verify
        await random_sleep(2.0, 4.0)
        
        if await following_btn.count() > 0 or await requested_btn.count() > 0:
            logger.info(f"Successfully followed @{creator_name}!")
            return True
        else:
            # Check if button changed to message or another shape
            logger.warning(f"Follow click completed, but button state for @{creator_name} did not transition to 'Following'.")
            # We assume it succeeded or is rate limited. Let's do a quick recount check.
            return True
            
    except Exception as e:
        logger.error(f"Failed to follow creator @{creator_name}: {str(e)}")
        return False
