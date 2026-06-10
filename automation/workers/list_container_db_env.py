import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run():
    url = os.environ.get("DATABASE_URL")
    print(f"Container DATABASE_URL: {url}")
    if not url:
        print("DATABASE_URL not set in container!")
        return
        
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, reel_url, status, created_at FROM reels ORDER BY created_at DESC"))
        rows = res.fetchall()
        print(f"Total reels: {len(rows)}")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(run())
