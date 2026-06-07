from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.reel import Reel
from app.models.dm_resource import DMResource
from app.models.creator_relationship import CreatorRelationship
from app.schemas.analytics import AnalyticsResponse, ConversionStats, CategoryCount, StatusCount, QueueMetrics
from app.queue.client import redis_client
from app.queue.constants import REELS_QUEUE, NOTION_SYNC_QUEUE, DEAD_LETTER_QUEUE
import logging

logger = logging.getLogger("analytics_router")
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("", response_model=AnalyticsResponse)
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db)):
    """
    Retrieve aggregated analytics for the Reelise dashboard.
    """
    # 1. Total reels counts
    stmt_total = select(func.count(Reel.id))
    stmt_completed = select(func.count(Reel.id)).where(Reel.status == "completed")
    stmt_failed = select(func.count(Reel.id)).where(Reel.status.in_(["failed", "dm_timeout"]))

    total_reels = (await db.execute(stmt_total)).scalar() or 0
    completed_reels = (await db.execute(stmt_completed)).scalar() or 0
    failed_reels = (await db.execute(stmt_failed)).scalar() or 0

    conversion_rate = 0.0
    if total_reels > 0:
        conversion_rate = round((completed_reels / total_reels) * 100, 2)

    conversion_stats = ConversionStats(
        total_reels=total_reels,
        completed_reels=completed_reels,
        failed_reels=failed_reels,
        conversion_rate=conversion_rate
    )

    # 2. Status distribution
    stmt_status = (
        select(Reel.status, func.count(Reel.id))
        .group_by(Reel.status)
    )
    status_res = await db.execute(stmt_status)
    status_counts = [
        StatusCount(status=row[0], count=row[1])
        for row in status_res.all()
    ]

    # 3. Category distribution
    stmt_cat = (
        select(DMResource.category, func.count(DMResource.id))
        .group_by(DMResource.category)
    )
    cat_res = await db.execute(stmt_cat)
    category_counts = [
        CategoryCount(category=row[0] or "Other", count=row[1])
        for row in cat_res.all()
    ]

    # 4. Total Resources
    stmt_res_count = select(func.count(DMResource.id))
    total_resources = (await db.execute(stmt_res_count)).scalar() or 0

    # 5. Total Creators Followed
    stmt_creators_followed = select(func.count(CreatorRelationship.id)).where(CreatorRelationship.followed == True)
    total_creators_followed = (await db.execute(stmt_creators_followed)).scalar() or 0

    # 6. Queue Metrics from Redis
    reels_len, notion_len, dlq_len = 0, 0, 0
    try:
        if await redis_client.ping():
            reels_len = await redis_client.llen(REELS_QUEUE)
            notion_len = await redis_client.llen(NOTION_SYNC_QUEUE)
            dlq_len = await redis_client.llen(DEAD_LETTER_QUEUE)
    except Exception as e:
        logger.error(f"Failed to fetch Redis queue lengths: {str(e)}")

    queue_metrics = QueueMetrics(
        reels_queue_length=reels_len,
        notion_queue_length=notion_len,
        dlq_queue_length=dlq_len
    )

    return AnalyticsResponse(
        overall_conversion=conversion_stats,
        status_distribution=status_counts,
        category_distribution=category_counts,
        queue_metrics=queue_metrics,
        total_resources=total_resources,
        total_creators_followed=total_creators_followed
    )
