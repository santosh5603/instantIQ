"""
Follow Agent — Follow/unfollow Instagram creators using instagrapi.

Replaces the Playwright-based follow_agent.py (106 lines of DOM button clicking)
with direct Instagram Private API calls.
"""

import logging
from instagrapi import Client
from instagrapi.exceptions import (
    UserNotFound,
    ClientError,
    FeedbackRequired,
    PleaseWaitFewMinutes,
)
from instagram.utils import sync_random_sleep

logger = logging.getLogger("follow_agent")


def _resolve_user_id(cl: Client, username: str) -> int | None:
    """Resolve an Instagram username to a user PK (numeric ID)."""
    try:
        user_id = cl.user_id_from_username(username)
        logger.info(f"Resolved @{username} -> user_id={user_id}")
        return user_id
    except UserNotFound:
        logger.error(f"User @{username} not found on Instagram.")
        return None
    except Exception as e:
        logger.error(f"Failed to resolve user_id for @{username}: {e}")
        return None


def is_following_creator(cl: Client, username: str) -> bool:
    """
    Check if the logged-in account is currently following the given creator.
    """
    user_id = _resolve_user_id(cl, username)
    if not user_id:
        return False

    try:
        friendship = cl.user_friendship_v1(user_id)
        is_following = friendship.following
        logger.info(f"Friendship with @{username}: following={is_following}")
        return is_following
    except Exception as e:
        logger.error(f"Error checking friendship with @{username}: {e}")
        return False


def follow_creator(cl: Client, username: str) -> bool:
    """
    Follow the given creator. Returns True if now following (or already was).
    Includes a human-like delay before the follow action.
    """
    logger.info(f"Attempting to follow @{username}...")

    user_id = _resolve_user_id(cl, username)
    if not user_id:
        return False

    # Check if already following
    try:
        friendship = cl.user_friendship_v1(user_id)
        if friendship.following:
            logger.info(f"Already following @{username}. Skipping.")
            return True
    except Exception as e:
        logger.warning(f"Could not check existing friendship for @{username}: {e}")

    # Human-like delay before following
    sync_random_sleep(2.0, 5.0)

    try:
        result = cl.user_follow(user_id)
        if result:
            logger.info(f"Successfully followed @{username}!")
            return True
        else:
            logger.warning(f"user_follow returned False for @{username}.")
            return False
    except FeedbackRequired as e:
        logger.error(f"Instagram feedback required (spam detection) when following @{username}: {e}")
        return False
    except PleaseWaitFewMinutes as e:
        logger.error(f"Rate limited when following @{username}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to follow @{username}: {e}")
        return False
