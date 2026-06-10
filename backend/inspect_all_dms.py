import os
import sys
from pathlib import Path
import json

# Setup paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root))

from instagram.session import get_instagrapi_client

def inspect_all():
    print("Initializing instagrapi client...")
    cl = get_instagrapi_client()
    
    print("Fetching direct threads (inbox)...")
    threads = cl.direct_threads(amount=20)
    print(f"Found {len(threads)} threads.")
    
    for i, thread in enumerate(threads):
        users = [u.username for u in thread.users]
        print(f"\n==================================================")
        print(f"THREAD [{i}] - ID: {thread.id} - Users: {users}")
        print(f"==================================================")
        
        try:
            messages = cl.direct_messages(thread.id, amount=10)
            print(f"Fetched {len(messages)} messages.")
            for j, msg in enumerate(messages):
                sender = "ME (suphero_toys)" if msg.user_id == cl.user_id else f"CREATOR ({msg.user_id})"
                for u in thread.users:
                    if u.pk == msg.user_id:
                        sender = u.username
                        break
                        
                print(f"  [{j}] From: {sender} | Msg ID: {msg.id} | Type: {msg.item_type} | Date: {msg.timestamp}")
                if msg.text:
                    print(f"    Text: {msg.text}")
                if msg.link:
                    print(f"    Link: {msg.link}")
                
                # Check for rich template components in raw_xma or generic_xma
                msg_dict = {}
                if hasattr(msg, "dict"):
                    msg_dict = msg.dict()
                elif hasattr(msg, "__dict__"):
                    msg_dict = msg.__dict__
                    
                raw_xma = msg_dict.get("raw_xma")
                if raw_xma and isinstance(raw_xma, dict):
                    generic_xma = raw_xma.get("generic_xma", [])
                    if generic_xma:
                        for idx, card in enumerate(generic_xma):
                            print(f"    [XMA Card {idx}] Title: {card.get('title_text')}")
                            cta_buttons = card.get("cta_buttons", [])
                            if cta_buttons:
                                print(f"      Buttons: {[{'title': b.get('title'), 'type': b.get('cta_type'), 'payload': b.get('platform_token', {}).get('postback', {}).get('postback_payload')} for b in cta_buttons]}")
                            target_url = card.get("target_url")
                            if target_url:
                                print(f"      Target URL: {target_url}")
                                
        except Exception as e:
            print(f"Error fetching messages for thread {thread.id}: {e}")

if __name__ == "__main__":
    inspect_all()
