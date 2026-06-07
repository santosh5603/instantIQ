"""
DM Reader — Scans the Instagram inbox for shared Reels using instagrapi.

Replaces the 538-line Playwright-based dm_listener.py with pure API calls.
No browser, no DOM scraping, no clicking.
"""

import logging
import re
from typing import List, Dict, Any

from instagrapi import Client
from instagrapi.types import DirectThread, DirectMessage

logger = logging.getLogger("dm_reader")


def extract_shortcode(url: str) -> str:
    """Extracts the unique shortcode from any Instagram URL."""
    match = re.search(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def scan_inbox_for_reels(cl: Client, admin_username: str, max_threads: int = 10) -> List[Dict[str, Any]]:
    """
    Scans the Instagram DM inbox for shared Reels/posts.

    Args:
        cl: Authenticated instagrapi Client.
        admin_username: The username of the admin account that sends reels
                        (used to filter the correct thread).
        max_threads: Maximum number of threads to fetch from the inbox.

    Returns:
        List of dicts: [{"sender_username": str, "reel_url": str, "message_id": str}]
    """
    logger.info(f"Scanning DM inbox for shared Reels (admin=@{admin_username})...")

    try:
        threads: List[DirectThread] = cl.direct_threads(amount=max_threads)
    except Exception as e:
        logger.error(f"Failed to fetch DM threads: {e}")
        return []

    if not threads:
        logger.info("No DM threads found in inbox.")
        return []

    extracted_reels: List[Dict[str, Any]] = []
    seen_urls: set = set()

    for thread in threads:
        # Check if any user in the thread matches the admin username
        thread_usernames = [u.username.lower() for u in thread.users]

        is_admin_thread = admin_username.lower() in thread_usernames

        if not is_admin_thread:
            continue

        logger.info(f"Found admin thread with @{admin_username} (thread_id={thread.id}). Scanning messages...")

        # Fetch recent messages from this thread
        try:
            messages: List[DirectMessage] = cl.direct_messages(thread.id, amount=20)
        except Exception as e:
            logger.error(f"Failed to fetch messages from thread {thread.id}: {e}")
            continue

        for msg in messages:
            # Resolve sender username locally to avoid rate limits
            sender_name = "unknown"
            if str(msg.user_id) == str(cl.user_id):
                sender_name = cl.username
            else:
                for u in thread.users:
                    if str(u.pk) == str(msg.user_id) or str(u.username) == str(msg.user_id):
                        sender_name = u.username
                        break

            reel_urls = []

            # 1. Check for media_share (shared posts/reels via the share button)
            if msg.media_share:
                try:
                    code = msg.media_share.code
                    if code:
                        media_type = msg.media_share.media_type
                        # media_type 2 = video (Reels), 1 = photo, 8 = carousel
                        type_str = "reel" if media_type == 2 else "p"
                        url = f"https://www.instagram.com/{type_str}/{code}/"
                        reel_urls.append(url)
                        logger.info(f"  Found media_share: {url} (media_type={media_type})")
                except Exception as e:
                    logger.warning(f"  Error extracting media_share: {e}")

            # 2. Check for clip (shared Reels via clips)
            if msg.clip:
                try:
                    code = msg.clip.media.code
                    if code:
                        url = f"https://www.instagram.com/reel/{code}/"
                        reel_urls.append(url)
                        logger.info(f"  Found clip share: {url}")
                except Exception as e:
                    logger.warning(f"  Error extracting clip: {e}")

            # 3. Check for reel/post URLs in text messages
            if msg.text:
                text_urls = re.findall(
                    r'https?://(?:www\.)?instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)',
                    msg.text
                )
                for code in text_urls:
                    url = f"https://www.instagram.com/reel/{code}/"
                    reel_urls.append(url)
                    logger.info(f"  Found URL in text: {url}")

            # 4. Check for XMA shares (Instagram's modern native sharing format, e.g. xma_clip)
            if hasattr(msg, "raw_xma") and isinstance(msg.raw_xma, dict):
                try:
                    xma_urls = _extract_urls_from_xma(msg.raw_xma)
                    for xma_url in xma_urls:
                        xma_match = re.search(
                            r'https?://(?:www\.)?instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)',
                            xma_url
                        )
                        if xma_match:
                            code = xma_match.group(1)
                            type_str = "reel" if "/reel/" in xma_url else "p"
                            url = f"https://www.instagram.com/{type_str}/{code}/"
                            reel_urls.append(url)
                            logger.info(f"  Found XMA clip/post share: {url}")
                except Exception as e:
                    logger.warning(f"  Error extracting from XMA: {e}")

            # Deduplicate, normalize to standard format, and add to results
            for url in reel_urls:
                code = extract_shortcode(url)
                if code:
                    norm_url = f"https://www.instagram.com/reel/{code}/"
                    if norm_url not in seen_urls:
                        seen_urls.add(norm_url)
                        extracted_reels.append({
                            "sender_username": sender_name,
                            "reel_url": norm_url,
                            "message_id": str(msg.id)
                        })

    logger.info(f"DM scan complete. Found {len(extracted_reels)} unique Reel URL(s).")
    return extracted_reels


def _extract_urls_from_xma(raw_xma: dict) -> List[str]:
    """Recursively extracts any 'target_url' values inside the XMA dictionary structure."""
    urls = []
    if not isinstance(raw_xma, dict):
        return urls

    for k, v in raw_xma.items():
        if k == "target_url" and isinstance(v, str):
            urls.append(v)
        elif isinstance(v, dict):
            urls.extend(_extract_urls_from_xma(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    urls.extend(_extract_urls_from_xma(item))
    return urls
