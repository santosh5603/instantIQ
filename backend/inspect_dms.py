import os
import sys
from pathlib import Path
import json

# Setup paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root))

from instagram.session import get_instagrapi_client

def inspect():
    print("Initializing instagrapi client...")
    cl = get_instagrapi_client()
    
    creator = "ashishbuilds"
    print(f"Fetching threads to find thread with @{creator}...")
    threads = cl.direct_threads(amount=10)
    
    target_thread = None
    for thread in threads:
        usernames = [u.username.lower() for u in thread.users]
        if creator.lower() in usernames:
            target_thread = thread
            break
            
    if not target_thread:
        print(f"No thread found with @{creator}.")
        return
        
    print(f"Found thread {target_thread.id} with users: {[u.username for u in target_thread.users]}")
    
    print("Fetching last 20 messages...")
    messages = cl.direct_messages(target_thread.id, amount=20)
    
    print("\n--- MESSAGE LIST (Newest First) ---")
    for i, msg in enumerate(messages):
        sender_username = "Unknown"
        if msg.user_id == cl.user_id:
            sender_username = "ME (suphero_toys)"
        else:
            for u in target_thread.users:
                if u.pk == msg.user_id:
                    sender_username = u.username
                    break
        
        print(f"\n[{i}] From: {sender_username} (ID: {msg.user_id}) | Msg ID: {msg.id} | Timestamp: {msg.timestamp}")
        print(f"Text: {msg.text}")
        print(f"Clip: {msg.clip}")
        
        msg_dict = {}
        if hasattr(msg, "dict"):
            msg_dict = msg.dict()
        elif hasattr(msg, "__dict__"):
            msg_dict = msg.__dict__
            
        # Print keys and some structure
        print("Keys:", list(msg_dict.keys()))
        
        # Dump entire dict for creator messages to inspect fields
        if sender_username != "ME (suphero_toys)":
            print("Full Message Dict:")
            print(json.dumps(msg_dict, default=str, indent=2))
            
        # Check for XMA / rich template components
        for k in ["xma", "xma_share", "xmas", "template", "carousel", "card", "cards", "buttons"]:
            if k in msg_dict and msg_dict[k]:
                print(f"Found Key '{k}': {json.dumps(msg_dict[k], indent=2)}")
                
        # If it has a generic raw data or custom fields
        raw_xma = msg_dict.get("xma_share") or msg_dict.get("xma")
        if raw_xma:
            print("RAW XMA Structure:")
            print(json.dumps(raw_xma, indent=2))
        else:
            # Let's inspect the keys and find if there's any dictionary
            for k, v in msg_dict.items():
                if isinstance(v, dict):
                    print(f"Dict Field '{k}': {list(v.keys())}")
                    # If it contains anything like header/body/footer or preview or template
                    if "header" in v or "body" in v or "template" in v or "title" in v:
                        print(json.dumps(v, indent=2))

if __name__ == "__main__":
    inspect()
