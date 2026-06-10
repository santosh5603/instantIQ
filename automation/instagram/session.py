"""
Instagrapi session management for the Reelise collector account.

Provides a singleton Client instance with persistent session storage,
automatic re-login on session expiry, and challenge handling.
"""
#bro i cant redbull in this damm house order kar jaldi se
import os
import logging
import json
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    FeedbackRequired,
    PleaseWaitFewMinutes,
)

logger = logging.getLogger("instagrapi_session")

_client: Client | None = None


def sync_session_to_playwright(cl: Client):
    """
    Takes authenticated instagrapi session cookies and writes them
    directly into Playwright's storage state JSON structure.
    This guarantees Playwright is authenticated without needing a separate login.
    """
    try:
        from config import settings
        playwright_session_path = Path(settings.INSTAGRAM_SESSION_PATH)
        
        # Gather cookies from all possible instagrapi internals
        target_cookies = {}
        
        # 1. Extract from authorization_data
        try:
            auth_data = cl.get_settings().get("authorization_data", {})
            if isinstance(auth_data, dict):
                if "sessionid" in auth_data:
                    target_cookies["sessionid"] = auth_data["sessionid"]
                if "ds_user_id" in auth_data:
                    target_cookies["ds_user_id"] = auth_data["ds_user_id"]
        except Exception as auth_err:
            logger.debug(f"Could not read from authorization_data: {auth_err}")
            
        # 2. Extract from requests CookieJar
        try:
            jar_cookies = cl.private.cookies.get_dict()
            for name, value in jar_cookies.items():
                target_cookies[name] = value
        except Exception as jar_err:
            logger.debug(f"Could not read requests cookies: {jar_err}")
            
        # 3. Extract from settings cookies
        try:
            settings_cookies = cl.get_settings().get("cookies", {})
            if isinstance(settings_cookies, dict):
                for name, value in settings_cookies.items():
                    target_cookies[name] = value
        except Exception as settings_err:
            logger.debug(f"Could not read settings cookies: {settings_err}")

        # 4. Fallback to client attributes if not resolved
        if "sessionid" not in target_cookies and hasattr(cl, "sessionid") and cl.sessionid:
            target_cookies["sessionid"] = cl.sessionid
            
        if "ds_user_id" not in target_cookies and hasattr(cl, "user_id") and cl.user_id:
            target_cookies["ds_user_id"] = str(cl.user_id)

        if not target_cookies or "sessionid" not in target_cookies:
            logger.warning("No authentication sessionid found to sync with Playwright.")
            return

        playwright_cookies = []
        for name, value in target_cookies.items():
            playwright_cookies.append({
                "name": name,
                "value": str(value),
                "domain": ".instagram.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True if name.lower() in ["sessionid", "rur", "shbts", "mid"] else False,
                "secure": True,
                "sameSite": "Lax"
            })
            
        storage_state = {
            "cookies": playwright_cookies,
            "origins": []
        }
        
        playwright_session_path.parent.mkdir(parents=True, exist_ok=True)
        with open(playwright_session_path, "w") as f:
            json.dump(storage_state, f, indent=2)
            
        logger.info(f"Synced instagrapi session cookies ({len(playwright_cookies)} cookies, including sessionid) directly to Playwright storage state at: {playwright_session_path}")
    except Exception as e:
        logger.error(f"Error syncing instagrapi cookies to Playwright: {e}")


def get_instagrapi_client() -> Client:
    """
    Returns a singleton instagrapi Client, logged in and ready to use.
    Loads a saved session if available; falls back to fresh login.
    Persists the session after every successful login/restore.
    """
    global _client
    if _client is not None:
        return _client

    from config import settings

    username = settings.INSTAGRAM_USERNAME
    password = settings.INSTAGRAM_PASSWORD
    session_path = Path(settings.INSTAGRAPI_SESSION_PATH)

    cl = Client()
    cl.delay_range = [1, 3]

    session_loaded = False

    if session_path.exists() and session_path.stat().st_size > 0:
        logger.info(f"Loading instagrapi session from: {session_path}")
        try:
            cl.load_settings(str(session_path))
            cl.login(username, password)
            try:
                cl.account_info()
                session_loaded = True
                logger.info("Instagrapi session restored and validated successfully.")
            except LoginRequired:
                logger.warning("Saved session expired. Performing fresh login...")
                session_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load saved session: {e}. Performing fresh login...")
            session_loaded = False

    if not session_loaded:
        logger.info(f"Performing fresh instagrapi login as @{username}...")
        cl = Client()
        cl.delay_range = [1, 3]
        try:
            cl.login(username, password)
            logger.info(f"Fresh login successful for @{username}.")
        except ChallengeRequired as e:
            logger.error(
                f"Instagram challenge required during login: {e}. "
                "Run scripts/create_session.py interactively to handle the challenge."
            )
            raise
        except FeedbackRequired as e:
            logger.error(f"Instagram feedback required (likely spam detection): {e}")
            raise
        except PleaseWaitFewMinutes as e:
            logger.error(f"Instagram rate limited: {e}")
            raise

    # Persist session
    session_path.parent.mkdir(parents=True, exist_ok=True)
    cl.dump_settings(str(session_path))
    logger.info(f"Session saved to {session_path}")

    # Synchronize session to Playwright
    sync_session_to_playwright(cl)

    _client = cl
    return _client


def reset_client():
    """Force-clear the singleton client so the next call to get_instagrapi_client() re-logs in."""
    global _client
    _client = None
    logger.info("Instagrapi client singleton has been reset.")
