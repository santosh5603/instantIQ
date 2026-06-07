"""
Comment Agent — Post comments on Instagram Reels using instagrapi.

Replaces the Playwright-based comment_agent.py (111 lines of textarea/button DOM
interactions) with a single instagrapi API call.
"""

import logging
from instagrapi import Client
from instagrapi.exceptions import (
    MediaNotFound,
    ClientError,
    FeedbackRequired,
    PleaseWaitFewMinutes,
)
from instagram.utils import sync_random_sleep

logger = logging.getLogger("comment_agent")


def post_comment(cl: Client, reel_url: str, keyword: str) -> bool:
    """
    Post a comment on the specified Reel URL with the given keyword text.

    Args:
        cl: Authenticated instagrapi Client.
        reel_url: Full Instagram Reel URL (e.g. https://www.instagram.com/reel/ABC123/)
        keyword: The comment text to post (typically the CTA keyword).

    Returns:
        True if comment posted successfully, False otherwise.
    """
    logger.info(f"Posting comment '{keyword}' on: {reel_url}")

    # 1. Resolve reel URL -> media PK
    try:
        media_pk = cl.media_pk_from_url(reel_url)
        if not media_pk:
            logger.error(f"Could not resolve media PK from URL: {reel_url}")
            return False
        logger.info(f"Resolved media PK: {media_pk}")
    except MediaNotFound:
        logger.error(f"Media not found for URL: {reel_url}")
        return False
    except Exception as e:
        logger.error(f"Error resolving media PK from {reel_url}: {e}")
        return False

    # 2. Convert PK to media_id (required by media_comment)
    try:
        media_id = cl.media_id(media_pk)
        logger.info(f"Resolved media ID: {media_id}")
    except Exception as e:
        logger.error(f"Error converting media PK to media ID: {e}")
        return False

    # 3. Check if already commented with the target keyword
    try:
        comments = cl.media_comments(media_id, amount=30)
        for c in comments:
            if c.user.username.lower() == cl.username.lower() and c.text.strip().upper() == keyword.strip().upper():
                logger.info(f"Already commented '{keyword}' on this Reel. Skipping duplicate posting.")
                return True
    except Exception as e:
        logger.warning(f"Could not check existing comments for {reel_url}: {e}")

    # 4. Human-like delay before commenting
    from config import settings
    delay_min = getattr(settings, "COMMENT_DELAY_MIN", 5)
    delay_max = getattr(settings, "COMMENT_DELAY_MAX", 15)
    logger.info(f"Waiting {delay_min}-{delay_max}s before posting comment...")
    sync_random_sleep(delay_min, delay_max)

    # 4. Post the comment
    try:
        comment = cl.media_comment(media_id, keyword)
        if comment:
            logger.info(f"Successfully posted comment (id={comment.pk}): '{keyword}'")
            return True
        else:
            logger.warning("media_comment returned falsy value.")
            return False
    except FeedbackRequired as e:
        logger.error(f"Instagram feedback required (spam detection): {e}")
        return False
    except PleaseWaitFewMinutes as e:
        logger.error(f"Rate limited when commenting: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to post comment on {reel_url}: {e}")
        return False
