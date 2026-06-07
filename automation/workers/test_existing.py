import asyncio
import sys
from pathlib import Path

# Setup paths
worker_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(worker_dir.parent / "backend"))
sys.path.insert(0, str(worker_dir.parent))

from workers.dm_listener_worker import _get_db_engine, _get_db_session
from app.models.reel import Reel
from sqlalchemy import select

def test():
    engine = _get_db_engine()
    print("Engine URL:", engine.url)
    session = _get_db_session(engine)
    url = "https://www.instagram.com/reel/DYuCCPlSGwd/"
    
    print(f"Querying database for URL: {url} ...")
    existing = session.execute(
        select(Reel).where(Reel.reel_url == url)
    ).scalar_one_or_none()
    
    print("Result:", existing)
    if existing:
        print(f"Row details: id={existing.id}, url={existing.reel_url}, status={existing.status}")
    else:
        print("No row found.")
        
    # Let's also query without trailing slash just in case
    url_no_slash = url.rstrip("/")
    existing_no = session.execute(
        select(Reel).where(Reel.reel_url == url_no_slash)
    ).scalar_one_or_none()
    print("Result (no slash):", existing_no)
    
if __name__ == "__main__":
    test()
