import asyncio
import sys
from pathlib import Path

# Setup paths
worker_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(worker_dir.parent / "backend"))
sys.path.insert(0, str(worker_dir.parent))

from base_worker import get_worker_db
from app.models.reel import Reel
from sqlalchemy import select

async def run():
    async with get_worker_db() as db:
        stmt = select(Reel).order_by(Reel.created_at.desc())
        res = await db.execute(stmt)
        reels = res.scalars().all()
        print(f"Container DB Total Reels: {len(reels)}")
        for r in reels:
            print(r.id, r.reel_url, r.status)

if __name__ == "__main__":
    asyncio.run(run())
