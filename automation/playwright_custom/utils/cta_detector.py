import re
from typing import Dict, Any, Optional

def detect_cta(caption: str) -> Dict[str, Any]:
    """
    Parses an Instagram Reel caption using layered regex patterns to detect:
    - If a comment is required, and the target keyword.
    - If the user must follow the creator first.
    - If a direct DM trigger is needed instead of a comment.
    
    Returns a dictionary of requirements and confidence.
    """
    if not caption:
        return {
            "requires_comment": False,
            "requires_follow": False,
            "requires_dm": False,
            "comment_keyword": None,
            "dm_keyword": None,
            "confidence": 0.0
        }

    clean_caption = re.sub(r'\s+', ' ', caption)
    caption_lower = clean_caption.lower()

    # Define standard trigger checks
    has_comment_trigger = any(w in caption_lower for w in ["comment", "reply", "type", "write", "drop", "leave"])
    has_follow_trigger = any(w in caption_lower for w in ["follow", "following", "subscribe", "add"])
    has_dm_trigger = any(w in caption_lower for w in ["dm", "message", "inbox", "send"])

    # If there are no trigger words whatsoever, it's not a CTA reel
    if not (has_comment_trigger or has_follow_trigger or has_dm_trigger):
        return {
            "requires_comment": False,
            "requires_follow": False,
            "requires_dm": False,
            "comment_keyword": None,
            "dm_keyword": None,
            "confidence": 0.0
        }

    requires_follow = False
    requires_comment = False
    requires_dm = False
    comment_keyword = None
    dm_keyword = None
    confidence = 0.0

    # 1. Follow check
    follow_patterns = [
        r'\bfollow\b',
        r'\bfollowing\b',
        r'\bsubscribe\b',
        r'\badd\b'
    ]
    for pattern in follow_patterns:
        if re.search(pattern, caption_lower):
            requires_follow = True
            confidence += 0.3
            break

    # List of trigger verbs and utility words to exclude as keywords
    verb_exclusions = {
        "comment", "reply", "type", "write", "drop", "leave", "word", "below",
        "me", "yes", "this", "now", "it", "here", "to", "and", "the", "a", "with",
        "dm", "send", "message", "inbox", "link", "get", "free", "your", "my", "our"
    }

    # 2. Extract Quoted Words as high-priority candidates
    # E.g. comment "GUIDE", reply 'AI', DM me "START"
    quoted_matches = re.findall(r"['\"“‘]([A-Za-z0-9_-]{2,15})['\"”’]", clean_caption)
    quoted_candidates = [w for w in quoted_matches if w.lower() not in verb_exclusions]

    # 3. Flexible Regex matcher for Comments and DMs
    # This allows optional bridging words like: "me a", "below with", "with the word", "me with the word"
    cta_regex = (
        r'\b(?:comment|reply|type|write|drop|dm|send|message)\b'       # Trigger Verb
        r'(?:\s+(?:me|us|below|with|the|word|a|an|your|our|free)){0,4}' # Optional bridging words (up to 4)
        r'\s+["\'“]?(?!(?:comment|reply|type|write|drop|leave|word|below|me|yes|this|now|it|here|to|and|the|a|with|dm|send|message|inbox|link|get|free|your|my|our)\b)([A-Za-z0-9_-]{2,15})["\'”]?' # Keyword Target with exclusions
    )

    matches = re.finditer(cta_regex, clean_caption, re.IGNORECASE)
    
    extracted_keyword = None
    extracted_is_dm = False

    for m in matches:
        keyword_candidate = m.group(1)
        # Exclude common bridging words and verbs
        if keyword_candidate.lower() not in verb_exclusions:
            extracted_keyword = keyword_candidate
            # Check if the trigger word in the match was a DM trigger
            matched_segment = m.group(0).lower()
            if any(dw in matched_segment for dw in ["dm", "send", "message"]):
                # If we have "send" or "dm" and a comment trigger is not prominent, mark as DM
                if not any(cw in matched_segment for cw in ["comment", "reply", "type"]):
                    extracted_is_dm = True
            break

    # 4. Fallbacks using quoted candidates if regex didn't resolve a valid keyword
    if not extracted_keyword and quoted_candidates:
        extracted_keyword = quoted_candidates[0]
        # Decide if it's comment or DM based on triggers
        if has_dm_trigger and not has_comment_trigger:
            extracted_is_dm = True

    # 5. Resolve requirements based on extraction
    if extracted_keyword:
        if extracted_is_dm:
            requires_dm = True
            dm_keyword = extracted_keyword.upper()
            confidence += 0.6
        else:
            requires_comment = True
            comment_keyword = extracted_keyword.upper()
            confidence += 0.6
    else:
        # If no explicit keyword was found, but follow is required
        if requires_follow:
            confidence = 0.3

    confidence = min(confidence, 1.0)

    return {
        "requires_comment": requires_comment,
        "requires_follow": requires_follow,
        "requires_dm": requires_dm,
        "comment_keyword": comment_keyword,
        "dm_keyword": dm_keyword,
        "confidence": confidence
    }
