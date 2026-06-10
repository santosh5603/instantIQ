import sys
from pathlib import Path

# Setup paths
worker_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(worker_dir.parent / "backend"))
sys.path.insert(0, str(worker_dir.parent))

from workers.dm_listener_worker import _get_db_engine, _get_db_session
from sqlalchemy import text

def clean_reels():
    engine = _get_db_engine()
    session = _get_db_session(engine)
    
    reels_to_delete = ['DYrsGTbz0Bd', 'DYuCCPlSGwd']
    
    for shortcode in reels_to_delete:
        print(f"Searching for shortcode: {shortcode} ...")
        res = session.execute(
            text("SELECT id FROM reels WHERE reel_url LIKE :pat"),
            {"pat": f"%{shortcode}%"}
        )
        row = res.fetchone()
        if row:
            reel_id = row[0]
            print(f"Found Reel ID {reel_id} for shortcode {shortcode}. Cleaning up...")
            
            # Delete process logs
            session.execute(text("DELETE FROM process_logs WHERE reel_id = :id"), {"id": reel_id})
            # Delete dm resources
            session.execute(text("DELETE FROM dm_resources WHERE reel_id = :id"), {"id": reel_id})
            # Delete reel
            session.execute(text("DELETE FROM reels WHERE id = :id"), {"id": reel_id})
            
            print(f"Successfully deleted {shortcode}!")
        else:
            print(f"Shortcode {shortcode} not found.")
            
    session.commit()
    print("Database cleanup complete!")

if __name__ == "__main__":
    clean_reels()
