import sys
from pathlib import Path

# Setup paths
worker_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(worker_dir.parent / "backend"))
sys.path.insert(0, str(worker_dir.parent))

from workers.dm_listener_worker import _get_db_engine, _get_db_session
from app.models.reel import Reel
from sqlalchemy import select, text

def list_all():
    engine = _get_db_engine()
    session = _get_db_session(engine)
    
    # Run a count query
    cnt = session.execute(text("SELECT COUNT(*) FROM reels")).scalar()
    print("Total Reels count in DB:", cnt)
    
    # List all rows
    res = session.execute(text("SELECT id, reel_url, creator_name, status, created_at FROM reels ORDER BY created_at DESC"))
    rows = res.fetchall()
    for r in rows:
        print(r)

if __name__ == "__main__":
    list_all()
