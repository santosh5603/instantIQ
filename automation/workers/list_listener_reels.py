import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run():
    url = os.environ.get("DATABASE_URL").replace(":6543/", ":5432/")
    print(f"Container DATABASE_URL: {url}")
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, reel_url, status FROM reels ORDER BY created_at DESC"))
        rows = res.fetchall()
        print(f"Total reels: {len(rows)}")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(run())
