"""
One-time script to create and persist an instagrapi session file.

Run this interactively on the VM/local machine before starting the Docker containers:
    python scripts/create_session.py

This handles:
- Initial login with username/password
- 2FA challenge resolution (if enabled)
- Saving the session JSON to session/instagrapi_session.json
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from automation directory
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
automation_env = project_root / "automation" / ".env"
load_dotenv(str(automation_env))

from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    TwoFactorRequired,
)


def main():
    username = os.getenv("INSTAGRAM_USERNAME", "kunalagar12100")
    password = os.getenv("INSTAGRAM_PASSWORD")
    session_path = os.getenv("INSTAGRAPI_SESSION_PATH", "session/instagrapi_session.json")

    # Make session path absolute relative to project root
    session_file = project_root / session_path
    session_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("REELISE: INSTAGRAPI SESSION CREATOR")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Session path: {session_file}")
    print("=" * 60)

    if not password:
        print("ERROR: INSTAGRAM_PASSWORD not set in .env")
        sys.exit(1)

    cl = Client()
    cl.delay_range = [1, 3]

    # Load existing session if available
    if session_file.exists() and session_file.stat().st_size > 0:
        print("Found existing session file. Attempting to restore...")
        try:
            cl.load_settings(str(session_file))
            cl.login(username, password)
            cl.account_info()
            print("SUCCESS: Existing session is still valid!")
            cl.dump_settings(str(session_file))
            print(f"Session saved to: {session_file}")
            return
        except Exception as e:
            print(f"Existing session expired or invalid: {e}")
            print("Performing fresh login...")
            cl = Client()
            cl.delay_range = [1, 3]

    # Fresh login
    try:
        cl.login(username, password)
        print("Login successful!")
    except TwoFactorRequired:
        print("\n2FA is enabled on this account.")
        code = input("Enter the 2FA code from your authenticator app: ").strip()
        cl.two_factor_login(code)
        print("2FA login successful!")
    except ChallengeRequired as e:
        print(f"\nInstagram challenge required: {e}")
        print("Please check your email/phone for a verification code.")
        # The challenge flow varies; instagrapi handles common patterns
        try:
            cl.challenge_resolve(cl.last_json)
            code = input("Enter the challenge code: ").strip()
            cl.challenge_code_handler(code)
            print("Challenge resolved!")
        except Exception as ce:
            print(f"Failed to resolve challenge: {ce}")
            print("Try again later or use a different network.")
            sys.exit(1)

    # Verify login
    try:
        info = cl.account_info()
        print(f"\nLogged in as: @{info.username} (pk={info.pk})")
    except Exception as e:
        print(f"WARNING: Could not verify login: {e}")

    # Save session
    cl.dump_settings(str(session_file))
    print(f"\nSUCCESS: Session saved to: {session_file}")

    # Verify file
    if session_file.exists() and session_file.stat().st_size > 0:
        print(f"File size: {session_file.stat().st_size} bytes")
        print("Session creation complete!")
    else:
        print("ERROR: Session file was not created properly.")
        sys.exit(1)


if __name__ == "__main__":
    main()
