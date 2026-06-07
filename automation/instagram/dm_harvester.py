"""
DM Harvester — Reads DM thread with a specific creator to harvest resources.

Replaces the Playwright-based dm_monitor.py (163 lines of DOM scraping)
with instagrapi API calls to read messages and extract links/files.
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional

from instagrapi import Client
from instagrapi.types import DirectThread, DirectMessage

logger = logging.getLogger("dm_harvester")


def extract_resources_and_buttons_from_xma(raw_xma: dict) -> Tuple[List[str], List[str]]:
    """
    Recursively extracts all external URLs and potential button titles/payloads
    from an XMA, attachment, or structured template dictionary payload.
    """
    urls = []
    button_texts = []
    
    if not isinstance(raw_xma, dict):
        return urls, button_texts

    for k, v in raw_xma.items():
        # 1. Look for URLs in any string field
        if isinstance(v, str):
            if v.startswith("http://") or v.startswith("https://"):
                if "instagram.com" not in v:
                    urls.append(v)
            # 2. Look for button text/titles
            # Common Meta/Instagram Graph API and ManyChat button keys:
            # "title", "text", "payload", "button_text", "action_title", "action_text", "button_title"
            if k in ["title", "text", "payload", "button_text", "action_title", "action_text", "button_title"] and len(v) < 60:
                val_clean = v.strip()
                # Exclude obvious non-button utility strings
                if val_clean and not val_clean.startswith("http") and not any(x in val_clean.lower() for x in ["http", "instagram", "facebook", "threads", "manychat"]):
                    button_texts.append(val_clean)
                    
        elif isinstance(v, dict):
            u, b = extract_resources_and_buttons_from_xma(v)
            urls.extend(u)
            button_texts.extend(b)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    u, b = extract_resources_and_buttons_from_xma(item)
                    urls.extend(u)
                    button_texts.extend(b)
                elif isinstance(item, str):
                    if item.startswith("http://") or item.startswith("https://"):
                        if "instagram.com" not in item:
                            urls.append(item)
                            
    return list(set(urls)), list(set(button_texts))


def harvest_dm_resources_and_buttons(cl: Client, creator_username: str) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Reads the DM thread with the specified creator and extracts:
    - Resource links/files
    - Button texts (for simulating taps on postback buttons)
    - Thread ID (for replying)

    Returns:
        Tuple of (resources, button_texts, thread_id)
    """
    logger.info(f"Harvesting DM resources & buttons from @{creator_username}...")

    resources: List[Dict[str, Any]] = []
    seen_links: set = set()
    button_texts: List[str] = []

    # 1. Find the thread with the creator
    try:
        threads: List[DirectThread] = cl.direct_threads(amount=20)
    except Exception as e:
        logger.error(f"Failed to fetch DM threads: {e}")
        return [], [], None

    target_thread = None
    for thread in threads:
        thread_usernames = [u.username.lower() for u in thread.users]
        if creator_username.lower() in thread_usernames:
            target_thread = thread
            break

    if not target_thread:
        logger.warning(f"No DM thread found with @{creator_username}.")
        return [], [], None

    logger.info(f"Found thread with @{creator_username} (thread_id={target_thread.id})")

    # 2. Fetch recent messages
    try:
        messages: List[DirectMessage] = cl.direct_messages(target_thread.id, amount=20)
    except Exception as e:
        logger.error(f"Failed to fetch messages from thread {target_thread.id}: {e}")
        return [], [], target_thread.id

    # 3. Resolve creator user_id for filtering sender
    creator_user_id = None
    for u in target_thread.users:
        if u.username.lower() == creator_username.lower():
            creator_user_id = u.pk
            break

    for msg in messages:
        # Only harvest messages FROM the creator (not from us)
        if creator_user_id and msg.user_id != creator_user_id:
            continue

        # 3a. Extract URLs from text messages
        if msg.text:
            urls = re.findall(r'(https?://[^\s\)]+)', msg.text)
            for url in urls:
                if "instagram.com" in url:
                    continue
                if url not in seen_links:
                    seen_links.add(url)
                    resources.append({
                        "resource_type": _detect_resource_type(url),
                        "resource_url": url,
                        "resource_text": f"Found link in DMs: {msg.text[:300]}",
                        "category": _detect_category(url),
                        "file_name": url.split("/")[-1][:80] if "/" in url else url[:80]
                    })

        # 3b. Extract from link item (when a link preview is sent)
        if msg.link:
            try:
                link_url = msg.link.link_url if hasattr(msg.link, 'link_url') else str(msg.link)
                link_text = msg.link.link_title if hasattr(msg.link, 'link_title') else ""
                if link_url and "instagram.com" not in link_url and link_url not in seen_links:
                    seen_links.add(link_url)
                    resources.append({
                        "resource_type": _detect_resource_type(link_url),
                        "resource_url": link_url,
                        "resource_text": f"Link preview: {link_text}",
                        "category": _detect_category(link_url),
                        "file_name": link_text[:80] if link_text else link_url.split("/")[-1][:80]
                    })
            except Exception as e:
                logger.warning(f"Error extracting link item: {e}")

        # 3c. Extract recursively from the raw message dictionary (XMA/generic templates/buttons/cards)
        try:
            msg_dict = {}
            if hasattr(msg, "dict"):
                msg_dict = msg.dict()
            elif hasattr(msg, "__dict__"):
                msg_dict = msg.__dict__
            
            if msg_dict:
                xma_urls, xma_buttons = extract_resources_and_buttons_from_xma(msg_dict)
                
                # Process extracted URLs
                for url in xma_urls:
                    if url not in seen_links:
                        seen_links.add(url)
                        resources.append({
                            "resource_type": _detect_resource_type(url),
                            "resource_url": url,
                            "resource_text": f"Extracted from rich template: {msg.text[:150] if msg.text else 'Attachment'}",
                            "category": _detect_category(url),
                            "file_name": url.split("/")[-1][:80] if "/" in url else url[:80]
                        })
                
                # Accumulate button titles for simulating taps
                for btn_text in xma_buttons:
                    if btn_text not in button_texts:
                        button_texts.append(btn_text)
        except Exception as e:
            logger.warning(f"Failed to extract rich XMA/template details from message {msg.id}: {e}")

    logger.info(f"Harvested {len(resources)} resource(s) and {len(button_texts)} button(s) from DMs with @{creator_username}.")
    return resources, button_texts, target_thread.id


def harvest_dm_resources(cl: Client, creator_username: str) -> List[Dict[str, Any]]:
    """
    Backwards-compatible wrapper.
    Reads the DM thread with the specified creator and extracts resource links/files.
    """
    resources, _, _ = harvest_dm_resources_and_buttons(cl, creator_username)
    return resources


def _detect_resource_type(url: str) -> str:
    """Detect resource type from URL."""
    url_lower = url.lower()
    if url_lower.endswith(".pdf") or "drive.google.com" in url_lower or "dropbox.com" in url_lower:
        return "pdf"
    elif any(ext in url_lower for ext in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]):
        return "document"
    elif any(ext in url_lower for ext in [".mp4", ".mov", ".avi"]):
        return "video"
    elif any(ext in url_lower for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
        return "image"
    elif any(ext in url_lower for ext in [".mp3", ".wav", ".ogg"]):
        return "audio"
    else:
        return "link"


def _detect_category(url: str) -> str:
    """Detect content category from URL keywords."""
    url_lower = url.lower()
    if any(kw in url_lower for kw in ["ai", "gpt", "llm", "claude", "openai"]):
        return "AI"
    elif any(kw in url_lower for kw in ["python", "js", "code", "github", "git", "dev"]):
        return "Programming"
    elif any(kw in url_lower for kw in ["career", "resume", "job", "hire", "interview"]):
        return "Career"
    elif any(kw in url_lower for kw in ["fit", "gym", "health", "workout", "nutrition"]):
        return "Fitness"
    elif any(kw in url_lower for kw in ["speak", "talk", "comm", "negotiate", "present"]):
        return "Communication"
    elif any(kw in url_lower for kw in ["market", "ads", "seo", "social", "brand"]):
        return "Marketing"
    else:
        return "Other"


def check_follow_required_in_dm(cl: Client, creator_username: str) -> bool:
    """
    Scans the latest messages in the DM thread from the creator to see if they
    are requesting the user to follow them first before receiving the resource.

    Args:
        cl: Authenticated instagrapi Client.
        creator_username: The username of the creator to check messages from.

    Returns:
        True if the creator sent a message containing follow-gated keywords, False otherwise.
    """
    logger.info(f"Checking DM thread with @{creator_username} for follow prompt...")

    try:
        threads: List[DirectThread] = cl.direct_threads(amount=5)
    except Exception as e:
        logger.error(f"Failed to fetch DM threads: {e}")
        return False

    target_thread = None
    for thread in threads:
        thread_usernames = [u.username.lower() for u in thread.users]
        if creator_username.lower() in thread_usernames:
            target_thread = thread
            break

    if not target_thread:
        logger.warning(f"No DM thread found with @{creator_username} to check follow prompt.")
        return False

    try:
        messages: List[DirectMessage] = cl.direct_messages(target_thread.id, amount=5)
    except Exception as e:
        logger.error(f"Failed to fetch messages from thread {target_thread.id}: {e}")
        return False

    creator_user_id = None
    for u in target_thread.users:
        if u.username.lower() == creator_username.lower():
            creator_user_id = u.pk
            break

    follow_keywords = ["follow", "following", "subscribe", "add me", "must follow", "follow first", "follow them"]
    
    for msg in messages:
        if creator_user_id and msg.user_id != creator_user_id:
            continue

        if msg.text:
            msg_lower = msg.text.lower()
            if any(kw in msg_lower for kw in follow_keywords):
                logger.info(f"Follow prompt detected in DM message: '{msg.text}'")
                return True

    logger.info(f"No follow prompt detected in DM thread with @{creator_username}.")
    return False
