import logging
import re
import json
from typing import Dict, Optional, Tuple
from playwright.async_api import Page
from ..utils.human_stealth import random_sleep
from config import settings

logger = logging.getLogger("reel_extractor")

def parse_creator_and_caption_from_meta(og_title: Optional[str], og_desc: Optional[str], meta_desc: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Parses creator username and caption from Instagram's HTML meta headers."""
    creator = None
    caption = None
    
    candidates = [og_desc, meta_desc, og_title]
    
    for text in candidates:
        if not text:
            continue
        text = text.strip()
        
        # Pattern 1a: "... - username on Month Day, Year: 'caption'"
        m = re.search(r'(?:^|\-\s+)([a-zA-Z0-9_\.]+)\s+on\s+[A-Za-z]+(?:\s+\d{1,2})?,\s+\d{4}:', text)
        if m:
            creator = m.group(1)
            cap = text[m.end():].strip()
            if cap.startswith('"') and cap.endswith('"'):
                cap = cap[1:-1]
            elif cap.startswith("'") and cap.endswith("'"):
                cap = cap[1:-1]
            caption = cap
            break

        # Pattern 1b: "... - DisplayName (@username) on Month Day, Year: 'caption'"
        m = re.search(r'\((?:@)?([a-zA-Z0-9_\.]+)\)\s+on\s+[A-Za-z]+(?:\s+\d{1,2})?,\s+\d{4}:', text)
        if m:
            creator = m.group(1)
            cap = text[m.end():].strip()
            if cap.startswith('"') and cap.endswith('"'):
                cap = cap[1:-1]
            elif cap.startswith("'") and cap.endswith("'"):
                cap = cap[1:-1]
            caption = cap
            break
            
        # Pattern 2: "username on Instagram: 'caption'"
        m = re.search(r'^([a-zA-Z0-9_\.]+)\s+on\s+Instagram:\s+["\']?(.*?)["\']?$', text, re.DOTALL)
        if m:
            creator = m.group(1)
            caption = m.group(2)
            break
            
        # Pattern 3: "@username on Instagram: 'caption'"
        m = re.search(r'^@([a-zA-Z0-9_\.]+)\s+on\s+Instagram:\s+["\']?(.*?)["\']?$', text, re.DOTALL)
        if m:
            creator = m.group(1)
            caption = m.group(2)
            break

        # Pattern 4: "DisplayName (@username) on Instagram: 'caption'"
        m = re.search(r'\((?:@)?([a-zA-Z0-9_\.]+)\)\s+on\s+Instagram:\s+["\']?(.*?)["\']?$', text, re.DOTALL)
        if m:
            creator = m.group(1)
            caption = m.group(2)
            break
            
        # Pattern 5: "Instagram photo by username" or "Instagram video by username"
        m = re.search(r'Instagram\s+(?:photo|video)\s+by\s+([a-zA-Z0-9_\.]+)', text)
        if m:
            creator = m.group(1)
            break

        # Pattern 6: "DisplayName (@username) on Instagram" or "DisplayName (@username) • Instagram"
        m = re.search(r'\((?:@)?([a-zA-Z0-9_\.]+)\)\s+on\s+Instagram', text)
        if m:
            creator = m.group(1)
            break

        m = re.search(r'\((?:@)?([a-zA-Z0-9_\.]+)\)\s+•\s+Instagram', text)
        if m:
            creator = m.group(1)
            break
            
    return creator, caption


async def extract_from_json_ld(page: Page) -> Tuple[Optional[str], Optional[str]]:
    """Extracts creator username and caption from application/ld+json structured schemas."""
    try:
        scripts = await page.locator("script[type='application/ld+json']").all()
        for script in scripts:
            try:
                content = await script.inner_text()
                if not content:
                    continue
                data = json.loads(content)
                
                # Check for single object or list of objects
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
                    
                for item in items:
                    author = item.get("author")
                    if author:
                        if isinstance(author, list):
                            author_data = author[0]
                        else:
                            author_data = author
                        
                        alternate_name = author_data.get("alternateName")
                        if alternate_name:
                            caption = item.get("articleBody") or item.get("description") or item.get("text")
                            logger.info(f"JSON-LD SUCCESS alternateName: @{alternate_name}")
                            return alternate_name, caption
                            
                        url = author_data.get("url")
                        if url and "instagram.com/" in url:
                            parts = url.split("instagram.com/")
                            if len(parts) > 1:
                                username = parts[1].strip("/").split("/")[0]
                                caption = item.get("articleBody") or item.get("description") or item.get("text")
                                logger.info(f"JSON-LD SUCCESS url parse: @{username}")
                                return username, caption
            except Exception as script_err:
                logger.debug(f"Failed parsing single JSON-LD script tag: {script_err}")
    except Exception as e:
        logger.warning(f"Error parsing application/ld+json: {e}")
    return None, None


async def extract_reel_metadata(page: Page, reel_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Navigates to the specified Instagram Reel URL, extracts the creator's username
    and the full caption text using a highly robust selector-agnostic strategy.
    
    Returns:
        Tuple[creator_name, caption]
    """
    logger.info(f"Extracting metadata from Reel URL: {reel_url}")
    
    try:
        # Navigate using domcontentloaded to prevent hanging on analytics/assets loading
        try:
            await page.goto(reel_url, wait_until="domcontentloaded", timeout=15000)
            await random_sleep(3.0, 4.0)
        except Exception as navigation_error:
            logger.warning(f"Playwright navigation warning (continuing anyway): {navigation_error}")

        creator_name = None
        caption = None

        # Priority 1: Schema-based extraction (application/ld+json)
        json_ld_creator, json_ld_caption = await extract_from_json_ld(page)
        if json_ld_creator:
            creator_name = json_ld_creator
            if json_ld_caption:
                caption = json_ld_caption

        # Priority 2: Page Title Parsing (100% immune to HTML DOM layout changes)
        if not creator_name:
            try:
                page_title = await page.title()
                if page_title:
                    # Look for "@username" or "(username)" inside title
                    m = re.search(r'\((?:@)?([a-zA-Z0-9_\.]+)\)', page_title)
                    if m:
                        creator_name = m.group(1)
                        logger.info(f"PAGE TITLE SUCCESS: @{creator_name}")
            except Exception as title_err:
                logger.warning(f"Could not parse page title: {title_err}")

        # Priority 3: Metadata-Based Parsing (100% selector-agnostic, immune to UI updates)
        try:
            og_title = await page.locator("meta[property='og:title']").get_attribute("content")
        except Exception:
            og_title = None
            
        try:
            og_desc = await page.locator("meta[property='og:description']").get_attribute("content")
        except Exception:
            og_desc = None
            
        try:
            meta_desc = await page.locator("meta[name='description']").get_attribute("content")
        except Exception:
            meta_desc = None

        meta_creator, meta_caption = parse_creator_and_caption_from_meta(og_title, og_desc, meta_desc)
        
        if meta_creator:
            creator_name = meta_creator
        if meta_caption:
            caption = meta_caption

        if creator_name and caption:
            logger.info(f"METADATA EXTRACTION STRATEGY SUCCESS: @{creator_name} | Caption length: {len(caption)}")
            return creator_name, caption

        # Logged in user to exclude from creator matching if we fall back
        logged_in_user = getattr(settings, "INSTAGRAM_USERNAME", "kunalagar12100")
        logger.info(f"Metadata parsing did not resolve full data (Creator={creator_name}, Caption={caption}). Falling back to selector scraping...")

        # 4. Selector-Based Creator Extraction
        if not creator_name:
            for a in await page.locator("a").all():
                href = await a.get_attribute("href")
                if href and href.startswith("/") and href.endswith("/"):
                    path = href.strip("/")
                    if "/" not in path and path.lower() not in [
                        logged_in_user.lower(), "explore", "direct", "emails", "about", 
                        "developer", "legal", "terms", "privacy", "directory", "jobs", 
                        "press", "api", "reels", "reel", "p"
                    ]:
                        if re.match(r'^[a-zA-Z0-9_\.]+$', path):
                            creator_name = path
                            logger.info(f"ROBUST EXTRACTED CREATOR: {creator_name}")
                            break

        if not creator_name:
            logger.warning("Could not extract creator name via robust anchor links")

        # 5. Selector-Based Caption Extraction
        if not caption:
            # Priority A: Username-prefixed span splitting (typical desktop post layouts)
            for span in await page.locator("span").all():
                text = await span.inner_text()
                if text:
                    text_cleaned = text.strip()
                    if creator_name and (
                        text_cleaned.startswith(creator_name + "\n") or 
                        text_cleaned.startswith(creator_name + "\xa0") or 
                        text_cleaned.startswith(creator_name + " ")
                    ):
                        lines = [l.strip() for l in text_cleaned.split("\n")]
                        lines = [l for l in lines if l and l != "\xa0"]
                        if len(lines) >= 2:
                            if lines[0] == creator_name:
                                if len(lines[1]) <= 4 and any(char.isdigit() for char in lines[1]):
                                    caption = "\n".join(lines[2:])
                                else:
                                    caption = "\n".join(lines[1:])
                                logger.info(f"ROBUST CAPTION (Priority A):\n{caption[:100]}...")
                                break
                                
            # Priority B: Fallback target selector
            if not caption:
                exclude_words = [
                    "home", "search", "explore", "reels", "messages", "notifications", 
                    "create", "profile", "more", "about", "blog", "jobs", "help", "api", 
                    "privacy", "terms", "locations", "popular", "instagram lite", "threads", 
                    "contact uploading & non-users", "meta verified", "meta ai", "english", 
                    "meta", "reply", "see translation", "view all"
                ]
                target_selector = "span.x193iq5w.xeuugli.x13faqbe.x1vvkbs"
                loc = page.locator(target_selector)
                for idx in range(await loc.count()):
                    text = await loc.nth(idx).inner_text()
                    text_cleaned = text.strip()
                    if text_cleaned.lower() in exclude_words or any(text_cleaned.lower().startswith(w) for w in ["view all", "reply"]):
                        continue
                    if creator_name and text_cleaned == creator_name:
                        continue
                    if text_cleaned and len(text_cleaned) > 5:
                        caption = text_cleaned
                        logger.info(f"ROBUST CAPTION (Priority B Fallback):\n{caption[:100]}...")
                        break
                        
        return creator_name, caption
        
    except Exception as e:
        logger.error(f"Failed to extract metadata from Reel '{reel_url}': {str(e)}")
        return None, None
