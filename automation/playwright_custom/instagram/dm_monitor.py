import logging
import re
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from ..utils.human_stealth import random_sleep

logger = logging.getLogger("dm_monitor")

async def open_creator_chat(page: Page, creator_name: str) -> bool:
    """
    Navigates to the creator's profile page and clicks the 'Message' button 
    to open the direct chat thread safely.
    """
    url = f"https://www.instagram.com/{creator_name}/"
    logger.info(f"Opening profile page to access chat: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await random_sleep(3.0, 5.0)
        
        # Locate "Message" button
        # Selectors: 
        # - div[role="button"]:has-text('Message')
        # - button:has-text('Message')
        msg_selectors = [
            "div[role='button']:has-text('Message')",
            "button:has-text('Message')",
            "a[href*='/direct/t/']"
        ]
        
        msg_btn = None
        for selector in msg_selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    msg_btn = locator.first
                    logger.info(f"Located Message button using selector: '{selector}'")
                    break
            except Exception:
                continue
                
        if not msg_btn:
            logger.error(f"Could not locate 'Message' button on @{creator_name}'s profile page.")
            return False
            
        await msg_btn.scroll_into_view_if_needed()
        await random_sleep(0.5, 1.5)
        await msg_btn.click()
        
        # Wait for chat thread to load
        await random_sleep(4.0, 7.0)
        logger.info(f"Successfully opened chat thread with @{creator_name}.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to navigate to chat with @{creator_name}: {str(e)}")
        return False

async def harvest_dm_responses(page: Page, creator_name: str) -> List[Dict[str, Any]]:
    """
    Scans the open chat thread for resources (links, files, or attachment text) 
    sent by the creator.
    """
    logger.info(f"Scanning chat bubbles with @{creator_name} for resources...")
    resources = []
    
    try:
        # 1. Fetch chat message text and links
        # Each chat message is typically rendered inside a div with role="row" or specific message bubbles
        # Let's extract all messages that are from the creator (not sent by us)
        # Instagram aligns our messages to the right, and incoming to the left.
        # Let's find links inside the chat window
        links_locator = page.locator("div[role='row'] a")
        link_count = await links_locator.count()
        
        logger.info(f"Found {link_count} total links in the active chat workspace.")
        
        seen_links = set()
        for i in range(link_count):
            try:
                link_loc = links_locator.nth(i)
                href = await link_loc.get_attribute("href")
                text = await link_loc.inner_text()
                
                if href:
                    # Filter out Instagram-internal links (e.g. profiles, reels, home links)
                    if "instagram.com" in href:
                        continue
                        
                    if href not in seen_links:
                        seen_links.add(href)
                        
                        # Detect category based on link keywords
                        category = "Other"
                        href_lower = href.lower()
                        if any(kw in href_lower for kw in ["ai", "gpt", "llm", "claude"]):
                            category = "AI"
                        elif any(kw in href_lower for kw in ["python", "js", "code", "github", "git"]):
                            category = "Programming"
                        elif any(kw in href_lower for kw in ["career", "resume", "job", "hire"]):
                            category = "Career"
                        elif any(kw in href_lower for kw in ["fit", "gym", "health", "workout"]):
                            category = "Fitness"
                        elif any(kw in href_lower for kw in ["speak", "talk", "comm", "negotiate"]):
                            category = "Communication"

                        # Determine resource type
                        res_type = "link"
                        if href.endswith(".pdf") or "drive.google.com" in href or "dropbox.com" in href:
                            res_type = "pdf"
                            
                        resources.append({
                            "resource_type": res_type,
                            "resource_url": href,
                            "resource_text": f"Found link in DMs: {text}",
                            "category": category,
                            "file_name": text or href.split("/")[-1][:80]
                        })
            except Exception as link_err:
                logger.error(f"Error harvesting link {i}: {str(link_err)}")
                continue

        # 2. Extract plain text messages from the creator if they sent a resource key
        # Selector for message bubbles (Instagram text elements):
        # We can extract text nodes inside message rows that don't have our message alignment styles.
        # However, a simpler way is checking text in the last 3 rows.
        rows_locator = page.locator("div[role='row']")
        row_count = await rows_locator.count()
        
        if row_count > 0:
            logger.info("Parsing last few messages for text-based keys...")
            # Inspect last 4 rows
            inspect_depth = min(row_count, 4)
            for r in range(row_count - inspect_depth, row_count):
                try:
                    row = rows_locator.nth(r)
                    row_text = await row.inner_text()
                    
                    # Look for URLs in plain text that were not marked as anchors
                    urls = re.findall(r'(https?://[^\s\)]+)', row_text)
                    for url in urls:
                        if "instagram.com" in url:
                            continue
                        if url not in seen_links:
                            seen_links.add(url)
                            resources.append({
                                "resource_type": "link",
                                "resource_url": url,
                                "resource_text": row_text[:300],
                                "category": "Other",
                                "file_name": url.split("/")[-1][:80]
                            })
                except Exception as row_err:
                    logger.error(f"Error checking text row {r}: {str(row_err)}")
                    continue
                    
        return resources
        
    except Exception as e:
        logger.error(f"Failed to harvest DM responses from @{creator_name}: {str(e)}")
        return []
