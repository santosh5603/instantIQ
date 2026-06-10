import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue

# Setup paths
worker_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(worker_dir.parent / "backend"))
sys.path.insert(0, str(worker_dir.parent))

from workers.dm_listener_worker import _get_db_engine, _get_db_session
from config import settings
from instagram.dm_reader import extract_shortcode
from sqlalchemy import text


def run_cleanup():
    print("==================================================")
    print("Database & Queue Cleansing Utility starting...")
    print("==================================================")

    # 1. Connect to DB and Redis
    engine = _get_db_engine()
    session = _get_db_session(engine)
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    reel_q = Queue("reelise:reel_queue", connection=redis_conn)
    notion_q = Queue("reelise:notion_sync_queue", connection=redis_conn)

    print("Successfully connected to Database and Redis.")

    # 2. Query all Reels
    res = session.execute(text("SELECT id, reel_url, status, created_at FROM reels ORDER BY created_at ASC"))
    reels = res.fetchall()
    print(f"Loaded {len(reels)} total Reels from DB.")

    shortcode_map = {}
    duplicates_to_delete = []
    updates_to_normalize = []

    # 3. Analyze duplicates and identify updates in memory
    for r_id, url, status, created_at in reels:
        shortcode = extract_shortcode(url)
        if not shortcode:
            print(f"Warning: Could not parse shortcode for Reel ID {r_id} (url={url}). skipping.")
            continue

        normalized_url = f"https://www.instagram.com/reel/{shortcode}/"
        
        # Check if we have already seen this shortcode
        if shortcode in shortcode_map:
            # We found a duplicate!
            prev_id, prev_status, prev_url = shortcode_map[shortcode]
            print(f"Found Duplicate for shortcode '{shortcode}':")
            print(f"  - Keep: ID={prev_id}, Status='{prev_status}', URL='{prev_url}'")
            print(f"  - Delete: ID={r_id}, Status='{status}', URL='{url}'")
            duplicates_to_delete.append(r_id)
        else:
            # This is the single canonical row we are keeping!
            shortcode_map[shortcode] = (r_id, status, normalized_url)
            if url != normalized_url:
                updates_to_normalize.append((r_id, normalized_url))

    # 4. Delete duplicates first (to prevent unique constraint violations on update)
    if duplicates_to_delete:
        print(f"\nDeleting {len(duplicates_to_delete)} duplicate Reels...")
        for dup_id in duplicates_to_delete:
            session.execute(text("DELETE FROM process_logs WHERE reel_id = :id"), {"id": dup_id})
            session.execute(text("DELETE FROM dm_resources WHERE reel_id = :id"), {"id": dup_id})
            session.execute(text("DELETE FROM reels WHERE id = :id"), {"id": dup_id})
        print("Duplicates successfully deleted.")

    # 5. Apply URL normalizations to the remaining rows
    if updates_to_normalize:
        print(f"\nNormalizing {len(updates_to_normalize)} Reel URLs...")
        for r_id, normalized_url in updates_to_normalize:
            # Ensure the row wasn't deleted as a duplicate
            if r_id not in duplicates_to_delete:
                print(f"  ID {r_id} -> '{normalized_url}'")
                session.execute(
                    text("UPDATE reels SET reel_url = :new_url WHERE id = :id"),
                    {"new_url": normalized_url, "id": r_id}
                )
        print("URLs successfully normalized.")

    # 6. Clean up old stuck pending reels from May 2026
    cutoff_time = datetime.utcnow() - timedelta(days=1)
    print(f"\nEvaluating historic active/pending jobs older than 1 day...")
    
    # We load them again post-deduplication
    res = session.execute(
        text("SELECT id, status, created_at FROM reels WHERE status IN ('pending', 'processing', 'waiting_dm', 'awaiting_follow', 'awaiting_comment')")
    )
    stuck_reels = res.fetchall()
    
    stuck_count = 0
    for r_id, status, created_at in stuck_reels:
        print(f"Stuck Reel ID {r_id}: Status='{status}', Created={created_at}")
        
        # Mark as dm_timeout to clear them cleanly
        session.execute(
            text("UPDATE reels SET status = 'dm_timeout', error_message = 'Marked as dm_timeout by cleansing utility to clear stale queue.' WHERE id = :id"),
            {"id": r_id}
        )
        stuck_count += 1

    print(f"Marked {stuck_count} stuck historic Reels as 'dm_timeout'.")

    # 7. Flush Redis Queues
    print("\nEmptying Redis queues...")
    
    reel_q_len = len(reel_q)
    notion_q_len = len(notion_q)
    
    reel_q.empty()
    notion_q.empty()
    
    print(f"Cleared {reel_q_len} jobs from reelise:reel_queue.")
    print(f"Cleared {notion_q_len} jobs from reelise:notion_sync_queue.")

    # Commit all DB transactions
    session.commit()
    session.close()
    engine.dispose()
    
    print("\n==================================================")
    print("Database & Queue Cleansing complete successfully!")
    print("==================================================")


if __name__ == "__main__":
    run_cleanup()
