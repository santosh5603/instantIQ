"""
Comments-Based CTA Detector — Intelligently resolves the CTA keyword of an Instagram Reel
by analyzing user comments and creator replies.
"""

import re
import logging
from typing import Optional, List, Dict
from instagrapi import Client
from instagrapi.exceptions import MediaNotFound, ClientError

logger = logging.getLogger("instagram.cta_detector")


def clean_keyword(text: str) -> str:
    """
    Cleans a comment text to extract potential keywords:
    - Removes user tags (e.g., @its_me.santoshh)
    - Removes non-alphanumeric characters (keeping only letters, numbers, spaces, hyphens, and underscores)
    - Strips whitespace
    - Converts to UPPERCASE
    """
    if not text:
        return ""
    # Remove user tags
    text_no_tags = re.sub(r'@[a-zA-Z0-9_\.]+', '', text)
    # Remove emojis and other special characters (keep words, spaces, hyphens, underscores)
    cleaned = re.sub(r'[^a-zA-Z0-9\s_-]', '', text_no_tags)
    return cleaned.strip().upper()


def detect_cta_from_comments(cl: Client, reel_url: str, creator_name: str) -> Optional[str]:
    """
    Analyzes the comments on the given Reel to determine the CTA keyword.
    
    Algorithm:
    1. Fetch the last 50 comments on the post.
    2. Group and count frequencies of short, cleaned candidate keywords.
    3. Rank candidate keywords by frequency descending.
    4. For the top 3 candidate keywords, check their replies:
       - If the creator replied to that comment.
       - If the creator's reply contains DM-related words (e.g., "check your dm", "sent").
    5. If a creator reply is verified, return that keyword immediately!
    6. Fallback: If no creator reply is verified, but a candidate keyword is extremely popular (>= 5 occurrences),
       return it as the most likely CTA keyword.
    """
    logger.info(f"Analyzing comments on Reel: {reel_url} (Creator: @{creator_name})")

    # 1. Resolve Reel URL -> Media PK & ID
    try:
        media_pk = cl.media_pk_from_url(reel_url)
        media_id = cl.media_id(media_pk)
    except MediaNotFound:
        logger.error(f"Media not found for URL: {reel_url}")
        return None
    except Exception as e:
        logger.error(f"Error resolving media ID for comment detection: {e}")
        return None

    # 2. Fetch recent comments
    try:
        comments = cl.media_comments(media_id, amount=50)
    except Exception as e:
        logger.error(f"Failed to fetch comments for {reel_url}: {e}")
        return None

    if not comments:
        logger.info("No comments found on this Reel.")
        return None

    logger.info(f"Retrieved {len(comments)} comments. Analyzing for candidate keywords...")

    # Exclusions for keywords (verbs and common stopwords)
    exclusions = {
        "COMMENT", "REPLY", "TYPE", "WRITE", "DROP", "LEAVE", "WORD", "BELOW",
        "ME", "YES", "THIS", "NOW", "IT", "HERE", "TO", "AND", "THE", "A", "WITH",
        "DM", "SEND", "MESSAGE", "INBOX", "LINK", "GET", "FREE", "YOUR", "MY", "OUR",
        "WANT", "PLEASE", "BRO", "HOW", "CAN", "YOU", "GIVE", "US", "INFO", "DETAILS"
    }

    # 3. Group comments by cleaned text
    keyword_groups: Dict[str, List] = {}
    for c in comments:
        # Ignore comments posted by the creator
        if creator_name and c.user.username.lower() == creator_name.lower():
            continue

        cleaned = clean_keyword(c.text)
        if not cleaned:
            continue

        # Ignore keywords that are too long (keywords are usually short, e.g. "NOTION", "GUIDE", "AI")
        if len(cleaned) > 20 or len(cleaned) < 2:
            continue

        # Ignore common exclusions
        if cleaned in exclusions:
            continue

        if cleaned not in keyword_groups:
            keyword_groups[cleaned] = []
        keyword_groups[cleaned].append(c)

    # 4. Rank candidate keywords by frequency descending
    candidates = sorted(
        keyword_groups.keys(),
        key=lambda k: len(keyword_groups[k]),
        reverse=True
    )

    if not candidates:
        logger.info("No valid CTA candidate keywords identified in comments.")
        return None

    logger.info(f"Identified candidates: {[(cand, len(keyword_groups[cand])) for cand in candidates[:5]]}")

    # DM keywords in creator replies to verify
    dm_reply_keywords = ["dm", "check", "sent", "inbox", "message", "send", "link", "delivered", "receive", "see"]

    # 5. Fetch replies for the top candidates (up to 3) to verify with creator replies
    for candidate in candidates[:3]:
        logger.info(f"Verifying candidate '{candidate}' (frequency: {len(keyword_groups[candidate])}) via replies...")
        
        # We check the first 3 comments in this keyword group to avoid too many API calls
        comments_to_check = keyword_groups[candidate][:3]
        for c in comments_to_check:
            try:
                # Fetch replies for this specific comment
                replies = cl.media_comment_replies(media_id, c.pk, amount=5)
                if not replies:
                    continue

                for r in replies:
                    # Check if the reply is by the creator
                    if creator_name and r.user.username.lower() == creator_name.lower():
                        # Check if reply text contains DM keywords
                        reply_lower = r.text.lower()
                        if any(kw in reply_lower for kw in dm_reply_keywords):
                            logger.info(f"100% VERIFIED: Creator @{creator_name} replied to comment '{c.text}' "
                                        f"with '{r.text}'. Confirmed CTA keyword: '{candidate}'")
                            return candidate
            except ClientError as ce:
                logger.warning(f"ClientError checking replies for comment {c.pk}: {ce}")
            except Exception as e:
                logger.warning(f"Error checking replies for comment {c.pk}: {e}")

    # 6. Fallback: If no creator reply is verified, but a candidate is extremely popular (>= 5 comments)
    top_candidate = candidates[0]
    top_freq = len(keyword_groups[top_candidate])
    if top_freq >= 5:
        logger.info(f"Fallback verification: Candidate '{top_candidate}' has high frequency ({top_freq}). "
                    f"Treating as CTA keyword without creator reply confirmation.")
        return top_candidate

    logger.info("Could not confidently identify any comments-based CTA keyword.")
    return None
