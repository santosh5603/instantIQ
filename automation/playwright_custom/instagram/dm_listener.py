import logging
import re
from typing import List, Dict, Any
from playwright.async_api import Page
from ..utils.human_stealth import random_sleep, human_scroll

logger = logging.getLogger("dm_listener")

async def scan_inbox_for_reels(page: Page) -> List[Dict[str, Any]]:
    """
    Navigates to the Instagram DM Inbox and scans active threads for shared Reels.
    
    Returns a list of extracted reel details:
    [{"sender_username": str, "reel_url": str, "message_id": str}]
    """
    logger.info("Navigating to Instagram Direct Inbox...")
    inbox_url = "https://www.instagram.com/direct/inbox/"
    
    # 0. Set a comprehensive exclusion list at the top of the function to avoid NameErrors
    exclude = ["explore", "reels", "direct", "requests", "about", "blog", "jobs", "help", "api", "privacy", "terms", "locations", "instagram", "emails", "stories", "p", "reel", "settings"]
    
    try:
        await page.goto(inbox_url, wait_until="networkidle", timeout=40000)
        await random_sleep(4.0, 7.0)
        
        # 1. Locate chat threads on the left panel
        thread_selector = "a[href^='/direct/t/'], div[role='button'].x1qjc9v5, div[role='button']:has-text(' · ')"
        thread_locators = page.locator(thread_selector)
        thread_count = await thread_locators.count()
        
        if thread_count == 0:
            logger.warning("No chat threads found in inbox.")
            return []
            
        logger.info(f"Found {thread_count} active chat threads in inbox. Scanning top 5 threads...")
        
        extracted_reels = []
        
        # Extract logged-in user dynamically from sidebar
        logged_in_user = "kunalagar12100" # fallback
        try:
            profile_link = page.locator("a:has-text('Profile')").first
            profile_href = await profile_link.get_attribute("href")
            if profile_href:
                logged_in_user = profile_href.strip("/").lower()
                logger.info(f"Dynamically identified logged-in user: @{logged_in_user}")
        except Exception as profile_err:
            logger.warning(f"Could not dynamically identify logged-in user: {str(profile_err)}")
        
        # Scan the top 5 threads to avoid spamming the account
        scan_limit = min(thread_count, 5)
        for i in range(scan_limit):
            try:
                # Re-fetch thread to avoid staleness after navigation
                thread = page.locator(thread_selector).nth(i)
                
                # Extract username or thread name
                thread_text = await thread.inner_text()
                lines = [line.strip() for line in thread_text.split("\n") if line.strip()]
                
                sender_username = "unknown"
                if len(lines) > 0:
                    sender_username = lines[0]
                
                # Build contact exclusion set
                contact_usernames = {sender_username.lower().replace("@", "").strip()}
                for line in lines:
                    cleaned = line.lower().replace("@", "").strip()
                    if cleaned and " " not in cleaned and "active" not in cleaned and "sent" not in cleaned:
                        contact_usernames.add(cleaned)
                
                # Try to extract actual handle from thread avatar image alt
                try:
                    avatar_img = thread.locator("img").first
                    alt_text = await avatar_img.get_attribute("alt")
                    if alt_text and "profile picture" in alt_text:
                        avatar_handle = alt_text.replace("'s profile picture", "").strip().lower()
                        if avatar_handle:
                            contact_usernames.add(avatar_handle)
                            logger.info(f"Extracted handle from avatar alt: @{avatar_handle}")
                except Exception:
                    pass
                
                logger.info(f"Scanning thread {i+1}/{scan_limit} with name '@{sender_username}' (Excluding: {contact_usernames})...")
                
                # Click the thread to open the chat window
                await thread.click()
                try:
                    await page.wait_for_selector("div[role='textbox']", timeout=12000)
                    logger.info("Chat textbox loaded successfully.")
                except Exception as t_err:
                    logger.warning(f"Timeout waiting for chat textbox to load: {str(t_err)}")
                await random_sleep(3.0, 5.0)
                
                # Try to extract actual handle from active chat header using robust JS-evaluation
                try:
                    header_handle = await page.evaluate("""() => {
                        const textbox = document.querySelector('div[role="textbox"]');
                        if (!textbox) return null;
                        
                        const chatPane = textbox.closest('div[role="main"]') || document.body;
                        
                        const headers = chatPane.querySelectorAll('header, [role="heading"], div[style*="height: 60px"], div[style*="height: 75px"]');
                        for (const h of headers) {
                            const links = h.querySelectorAll('a[href^="/"]');
                            for (const link of links) {
                                const href = link.getAttribute('href');
                                if (href) {
                                    const parts = href.split('/').filter(Boolean);
                                    if (parts.length === 1 && !['direct', 'explore', 'reels', 'requests'].includes(parts[0])) {
                                        return parts[0];
                                    }
                                }
                            }
                        }
                        
                        const links = Array.from(chatPane.querySelectorAll('a[href^="/"]'));
                        for (const link of links) {
                            const href = link.getAttribute('href');
                            if (href) {
                                const parts = href.split('/').filter(Boolean);
                                if (parts.length === 1 && !['direct', 'explore', 'reels', 'requests'].includes(parts[0])) {
                                    const rect = link.getBoundingClientRect();
                                    if (rect.top < 200) {
                                        return parts[0];
                                    }
                                }
                            }
                        }
                        return null;
                    }""")
                    
                    if header_handle:
                        header_handle_cleaned = header_handle.strip().lower()
                        if header_handle_cleaned and header_handle_cleaned not in exclude:
                            contact_usernames.add(header_handle_cleaned)
                            logger.info(f"Extracted contact handle from active chat header: @{header_handle_cleaned}")
                except Exception as header_err:
                    logger.warning(f"Could not extract contact handle from header: {str(header_err)}")
                
                # 2. Scroll chat thread to bottom to load latest messages/Reel cards
                try:
                    scroll_res = await page.evaluate("""() => {
                        const scrollableElement = document.querySelector('div[style*="overflow-y: auto"], div[style*="overflow: hidden auto"], div.x5yr21d.x1n2onr6');
                        if (scrollableElement) {
                            scrollableElement.scrollTop = scrollableElement.scrollHeight;
                            return "overflow_div";
                        }
                        const lists = document.querySelectorAll('div[role="list"], div[role="presentation"]');
                        for (const list of lists) {
                            if (list.scrollHeight > list.clientHeight) {
                                list.scrollTop = list.scrollHeight;
                                return "role_list";
                            }
                        }
                        window.scrollTo(0, document.body.scrollHeight);
                        return "window";
                    }""")
                    logger.info(f"Scrolled chat window using: {scroll_res}")
                    await random_sleep(2.5, 4.0)
                except Exception as scroll_err:
                    logger.warning(f"Could not scroll chat window: {str(scroll_err)}")
                
                try:
                    hrefs = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => {
                                const href = a.getAttribute('href');
                                if (!href) return null;
                                try {
                                    if (href.startsWith('http://') || href.startsWith('https://')) {
                                        const url = new URL(href);
                                        if (url.hostname.includes('instagram.com')) {
                                            return url.pathname + url.search + url.hash;
                                        }
                                        return href;
                                    }
                                } catch (e) {}
                                return href;
                            })
                            .filter(Boolean);
                    }""")
                except Exception as eval_err:
                    logger.warning(f"Failed to evaluate page links: {str(eval_err)}")
                    hrefs = []
                
                # Print all relative deep links for debugging
                deep_links = [h for h in hrefs if "/reel/" in h or "/p/" in h]
                logger.info(f"ALL DEEP LINKS IN CHAT: {deep_links}")
                
                # Directly extract any Reel/Post links from the chat page without clicking
                for href in hrefs:
                    if not href:
                        continue
                    if "/reel/" in href or "/p/" in href:
                        match = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)', href)
                        if match:
                            code = match.group(1)
                            is_post = "/p/" in href
                            type_str = "p" if is_post else "reel"
                            reel_url = f"https://www.instagram.com/{type_str}/{code}/"
                            
                            message_id = f"dm-{sender_username}-{hash(reel_url)}"
                            
                            # Add if not already extracted in this run
                            if reel_url not in [r["reel_url"] for r in extracted_reels]:
                                logger.info(f"Directly extracted shared Reel URL from chat links: {reel_url}")
                                extracted_reels.append({
                                    "sender_username": sender_username,
                                    "reel_url": reel_url,
                                    "message_id": message_id
                                })
                
                # Extract candidate creator usernames from the hrefs
                candidate_paths = []
                for href in hrefs:
                    if not href:
                        continue
                    path = href.strip("/")
                    if not path or "/" in path or "#" in path:
                        continue
                        
                    if path.lower() in exclude:
                        continue
                        
                    # Exclude contact usernames
                    if path.lower().strip() in contact_usernames:
                        continue
                        
                    # Exclude logged in user
                    if path.lower().strip() == logged_in_user.lower().strip():
                        continue
                        
                    if path not in candidate_paths:
                        candidate_paths.append(path)
                
                logger.info(f"Scanning chat window: Found {len(candidate_paths)} candidate creator profile link(s): {candidate_paths}")
                
                # We will check each creator link to see if it is a shared Reel card in the chat window
                for idx, path in enumerate(candidate_paths):
                    try:
                        logger.info(f"  [Creator {idx+1}/{len(candidate_paths)}] Attempting to click card cover for @{path}...")
                        
                        # Debug: Print the card outer HTML to see the DOM structure
                        try:
                            card_html = await page.evaluate("""(p) => {
                                const creatorLink = Array.from(document.querySelectorAll('a'))
                                    .reverse()
                                    .find(a => {
                                        const href = a.getAttribute('href');
                                        return href && (href === `/${p}/` || href === `/${p}`);
                                    });
                                if (!creatorLink) return "No creator link found";
                                
                                let current = creatorLink;
                                let depth = 0;
                                while (current && current.tagName !== 'BODY' && depth < 10) {
                                    if (current.getAttribute('role') === 'row' || current.matches('div[role="row"]')) {
                                        break;
                                    }
                                    current = current.parentElement;
                                    depth++;
                                }
                                return current ? current.outerHTML : "No container found";
                            }""", path)
                            logger.info(f"DEBUG CARD HTML (first 1500 chars):\n{card_html[:1500]}")
                        except Exception as html_err:
                            logger.warning(f"Could not print card HTML: {str(html_err)}")
                        
                        start_url = page.url
                        has_clicked = False
                        
                        # Use robust coordinate-based trusted click strategy
                        try:
                            logger.info(f"Finding best clickable coordinates for card cover @{path}...")
                            click_coords = await page.evaluate("""(p) => {
                                const creatorLink = Array.from(document.querySelectorAll('a'))
                                    .reverse()
                                    .find(a => {
                                        const href = a.getAttribute('href');
                                        return href && (href === `/${p}/` || href === `/${p}`);
                                    });
                                if (!creatorLink) return { found: false };
                                
                                const creatorLinkRect = creatorLink.getBoundingClientRect();
                                let current = creatorLink;
                                let bestClickable = null;
                                let maxArea = 0;
                                let depth = 0;
                                
                                while (current && current.tagName !== 'BODY' && depth < 8) {
                                    const clickables = Array.from(current.querySelectorAll('div[role="button"], img, video, canvas, div.x1ey2m1c, div.x1uhb9sk, div.xjbqb8w'));
                                    for (const el of clickables) {
                                        if (creatorLink.contains(el)) continue;
                                        
                                        const rect = el.getBoundingClientRect();
                                        const area = rect.width * rect.height;
                                        
                                        // Specific shared Reel cover boundaries
                                        if (rect.width >= 100 && rect.width <= 350 && 
                                            rect.height >= 150 && rect.height <= 550 && 
                                            Math.abs(rect.left - creatorLinkRect.left) < 80 &&
                                            rect.top > creatorLinkRect.top - 20) {
                                            
                                            if (area > maxArea) {
                                                maxArea = area;
                                                bestClickable = el;
                                            }
                                        }
                                    }
                                    
                                    if (current.getAttribute('role') === 'row' || current.matches('div[role="row"]') || current.classList.contains('x1ga7v0g')) {
                                        break;
                                    }
                                    current = current.parentElement;
                                    depth++;
                                }
                                
                                // Fallback to any visual elements inside row if specific cover not found
                                if (!bestClickable) {
                                    current = creatorLink;
                                    depth = 0;
                                    while (current && current.tagName !== 'BODY' && depth < 8) {
                                        const clickables = Array.from(current.querySelectorAll('img, video, canvas'));
                                        for (const el of clickables) {
                                            if (creatorLink.contains(el)) continue;
                                            const rect = el.getBoundingClientRect();
                                            const area = rect.width * rect.height;
                                            if (rect.width > 50 && rect.height > 50 && area > maxArea) {
                                                maxArea = area;
                                                bestClickable = el;
                                            }
                                        }
                                        if (current.getAttribute('role') === 'row' || current.matches('div[role="row"]')) {
                                            break;
                                        }
                                        current = current.parentElement;
                                        depth++;
                                    }
                                }
                                
                                if (bestClickable) {
                                    bestClickable.scrollIntoView({ block: 'center', inline: 'center' });
                                    const rect = bestClickable.getBoundingClientRect();
                                    return {
                                        x: rect.left + rect.width / 2,
                                        y: rect.top + rect.height / 2,
                                        found: true
                                    };
                                }
                                return { found: false };
                            }""", path)
                            
                            if click_coords.get("found"):
                                await random_sleep(1.5, 2.0) # Wait for scrolling animation
                                # Re-evaluate coordinates after scrolling finishes to get precise viewport coords
                                click_coords = await page.evaluate("""(p) => {
                                    const creatorLink = Array.from(document.querySelectorAll('a'))
                                        .reverse()
                                        .find(a => {
                                            const href = a.getAttribute('href');
                                            return href && (href === `/${p}/` || href === `/${p}`);
                                        });
                                    if (!creatorLink) return { found: false };
                                    
                                    const creatorLinkRect = creatorLink.getBoundingClientRect();
                                    let current = creatorLink;
                                    let bestClickable = null;
                                    let maxArea = 0;
                                    let depth = 0;
                                    
                                    while (current && current.tagName !== 'BODY' && depth < 8) {
                                        const clickables = Array.from(current.querySelectorAll('div[role="button"], img, video, canvas, div.x1ey2m1c, div.x1uhb9sk, div.xjbqb8w'));
                                        for (const el of clickables) {
                                            if (creatorLink.contains(el)) continue;
                                            
                                            const rect = el.getBoundingClientRect();
                                            const area = rect.width * rect.height;
                                            
                                            // Specific shared Reel cover boundaries
                                            if (rect.width >= 100 && rect.width <= 350 && 
                                                rect.height >= 150 && rect.height <= 550 && 
                                                Math.abs(rect.left - creatorLinkRect.left) < 80 &&
                                                rect.top > creatorLinkRect.top - 20) {
                                                
                                                if (area > maxArea) {
                                                    maxArea = area;
                                                    bestClickable = el;
                                                }
                                            }
                                        }
                                        
                                        if (current.getAttribute('role') === 'row' || current.matches('div[role="row"]') || current.classList.contains('x1ga7v0g')) {
                                            break;
                                        }
                                        current = current.parentElement;
                                        depth++;
                                    }
                                    
                                    // Fallback to any visual elements inside row if specific cover not found
                                    if (!bestClickable) {
                                        current = creatorLink;
                                        depth = 0;
                                        while (current && current.tagName !== 'BODY' && depth < 8) {
                                            const clickables = Array.from(current.querySelectorAll('img, video, canvas'));
                                            for (const el of clickables) {
                                                if (creatorLink.contains(el)) continue;
                                                const rect = el.getBoundingClientRect();
                                                const area = rect.width * rect.height;
                                                if (rect.width > 50 && rect.height > 50 && area > maxArea) {
                                                    maxArea = area;
                                                    bestClickable = el;
                                                }
                                            }
                                            if (current.getAttribute('role') === 'row' || current.matches('div[role="row"]')) {
                                                break;
                                            }
                                            current = current.parentElement;
                                            depth++;
                                        }
                                    }
                                    
                                    if (bestClickable) {
                                        const rect = bestClickable.getBoundingClientRect();
                                        return {
                                            x: rect.left + rect.width / 2,
                                            y: rect.top + rect.height / 2,
                                            found: true
                                        };
                                    }
                                    return { found: false };
                                }""", path)
                                
                                x = click_coords["x"]
                                y = click_coords["y"]
                                logger.info(f"Moving mouse and clicking card cover at coordinates ({x}, {y})")
                                await page.mouse.move(x, y)
                                await random_sleep(0.3, 0.7)
                                await page.mouse.click(x, y)
                                has_clicked = True
                            else:
                                logger.warning(f"Could not find visual media element inside card cover for creator @{path}")
                        except Exception as click_eval_err:
                            logger.warning(f"Coordinate Click evaluation error: {str(click_eval_err)}")
                            has_clicked = False
                            
                        if not has_clicked:
                            logger.info("No large images/videos clicked via coords. Clicking profile link as fallback...")
                            try:
                                await page.locator(f"a[href='/{path}/'], a[href='/{path}']").first.click(timeout=8000)
                                has_clicked = True
                            except Exception as fallback_err:
                                logger.warning(f"Playwright click fallback failed: {str(fallback_err)}")
                                
                        if has_clicked:
                            # Wait for navigation to complete
                            await random_sleep(5.0, 7.0)
                            current_url = page.url
                            logger.info(f"Navigated URL after click: {current_url}")
                            
                            # Debug screenshot to confirm visual state after click
                            if "/reel/" not in current_url and "/p/" not in current_url:
                                debug_shot_path = f"/app/backend/click_debug_{path}.png"
                                try:
                                    await page.screenshot(path=debug_shot_path)
                                    logger.info(f"Saved click debug screenshot to {debug_shot_path}")
                                except Exception as screenshot_err:
                                    logger.warning(f"Could not save click debug screenshot: {str(screenshot_err)}")
                            
                            # Check if we successfully navigated to a reel or post
                            if "/reel/" in current_url or "/p/" in current_url:
                                match = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)', current_url)
                                if match:
                                    code = match.group(1)
                                    is_post = "/p/" in current_url
                                    type_str = "p" if is_post else "reel"
                                    reel_url = f"https://www.instagram.com/{type_str}/{code}/"
                                    
                                    logger.info(f"Successfully captured Reel URL from navigation: {reel_url}")
                                    
                                    message_id = f"dm-{sender_username}-{hash(reel_url)}"
                                    
                                    extracted_reels.append({
                                        "sender_username": sender_username,
                                        "reel_url": reel_url,
                                        "message_id": message_id
                                    })
                                    
                            # Return back to the chat using page.go_back() if we actually navigated away
                            if current_url != start_url:
                                logger.info("Returning back to DM chat window...")
                                try:
                                    await page.go_back(timeout=8000)
                                    await page.wait_for_selector("div[role='textbox']", timeout=12000)
                                except Exception as back_err:
                                    logger.warning(f"Error or timeout returning to inbox: {str(back_err)}")
                                    # Fallback recovery: navigate back to the inbox and re-open the current thread
                                    logger.info(f"Attempting fallback recovery for thread {i+1}...")
                                    try:
                                        await page.goto(inbox_url, wait_until="networkidle", timeout=30000)
                                        await random_sleep(3.0, 5.0)
                                        thread = page.locator(thread_selector).nth(i)
                                        await thread.click()
                                        await page.wait_for_selector("div[role='textbox']", timeout=15000)
                                        # Scroll to bottom
                                        await page.evaluate("""() => {
                                            const scrollableElement = document.querySelector('div[style*="overflow-y: auto"], div[style*="overflow: hidden auto"], div.x5yr21d.x1n2onr6');
                                            if (scrollableElement) {
                                                scrollableElement.scrollTop = scrollableElement.scrollHeight;
                                            }
                                        }""")
                                        logger.info("Fallback recovery: DM chat window restored successfully.")
                                    except Exception as recovery_err:
                                        logger.error(f"Fallback recovery failed for thread {i+1}: {str(recovery_err)}")
                                await random_sleep(2.0, 3.0)
                            
                    except Exception as path_err:
                        logger.warning(f"Error processing creator {path}: {str(path_err)}")
                        continue
                                
            except Exception as thread_err:
                logger.error(f"Error scanning thread {i+1}: {str(thread_err)}")
                continue
                
        # Deduplicate
        unique_reels = []
        seen_urls = set()
        for r in extracted_reels:
            if r["reel_url"] not in seen_urls:
                seen_urls.add(r["reel_url"])
                unique_reels.append(r)
                
        return unique_reels
        
    except Exception as e:
        logger.error(f"Failed to scan direct message inbox: {str(e)}")
        return []
