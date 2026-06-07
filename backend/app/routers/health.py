from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.queue.client import redis_client
from app.queue.constants import REELS_QUEUE, NOTION_SYNC_QUEUE, DEAD_LETTER_QUEUE
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["Health & Status"])

@router.get("", response_model=Dict[str, Any])
async def check_health(db: AsyncSession = Depends(get_db)):
    """
    Checks backend API health including Postgres DB connectivity, 
    Redis queue connectivity, and current queue depths.
    """
    db_ok = False
    db_error = None
    try:
        # Check DB
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_error = str(e)

    redis_ok = False
    redis_error = None
    queue_depths = {
        "reels": 0,
        "notion_sync": 0,
        "dead_letter": 0
    }
    
    try:
        # Check Redis
        ping_res = await redis_client.ping()
        if ping_res:
            redis_ok = True
            # Fetch queue depths
            queue_depths["reels"] = await redis_client.llen(REELS_QUEUE)
            queue_depths["notion_sync"] = await redis_client.llen(NOTION_SYNC_QUEUE)
            queue_depths["dead_letter"] = await redis_client.llen(DEAD_LETTER_QUEUE)
    except Exception as e:
        redis_error = str(e)

    status = "healthy"
    if not db_ok or not redis_ok:
        status = "degraded"

    return {
        "status": status,
        "database": {
            "connected": db_ok,
            "error": db_error
        },
        "redis": {
            "connected": redis_ok,
            "error": redis_error
        },
        "queues": queue_depths
    }
