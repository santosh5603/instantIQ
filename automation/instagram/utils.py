"""
Shared utility functions for the instagrapi-based Instagram modules.
Non-Playwright random sleep with jitter for human-like timing.
"""

import asyncio
import random
import time
import logging

logger = logging.getLogger("instagram_utils")


async def async_random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Async sleep for a random duration between min_seconds and max_seconds."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Async sleeping for {delay:.2f}s...")
    await asyncio.sleep(delay)


def sync_random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Synchronous sleep for a random duration between min_seconds and max_seconds."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sync sleeping for {delay:.2f}s...")
    time.sleep(delay)
