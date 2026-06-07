import asyncio
import random
import logging
from playwright.async_api import Page, Locator

logger = logging.getLogger("human_stealth")

async def random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """
    Sleeps for a random duration between min_seconds and max_seconds.
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sleeping for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

async def human_type(locator: Locator, text: str, delay_min_ms: int = 50, delay_max_ms: int = 150):
    """
    Types text into a field with randomized keystroke intervals to mimic human typing.
    """
    await locator.click()
    for char in text:
        await locator.type(char, delay=0)  # Type character instantly
        # Sleep a random amount of time between keystrokes
        keystroke_delay = random.uniform(delay_min_ms / 1000.0, delay_max_ms / 1000.0)
        await asyncio.sleep(keystroke_delay)
    
    # Small pause after typing finishes
    await random_sleep(0.5, 1.5)

async def human_scroll(page: Page, direction: str = "down", distance_min: int = 100, distance_max: int = 300):
    """
    Performs a smooth, human-like scroll action.
    """
    distance = random.randint(distance_min, distance_max)
    if direction == "up":
        distance = -distance
        
    # Scroll in small increments
    steps = random.randint(5, 10)
    step_distance = distance / steps
    
    for _ in range(steps):
        await page.evaluate(f"window.scrollBy(0, {step_distance})")
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
    await random_sleep(0.5, 1.5)
