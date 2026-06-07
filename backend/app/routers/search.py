from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from app.database import get_db
from app.models.dm_resource import DMResource
from app.models.reel import Reel
from app.schemas.resource import ResourceResponse
from app.schemas.common import APIResponse
from typing import List

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("", response_model=APIResponse[List[ResourceResponse]])
async def search_resources(
    q: str = Query(..., min_length=1, description="Keyword search query"),
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Search harvested resources across file names, URLs, parsed message text, 
    and original reel captions or creator names.
    """
    # Build a joined search query
    stmt = (
        select(DMResource)
        .join(Reel, DMResource.reel_id == Reel.id)
        .where(
            or_(
                DMResource.file_name.ilike(f"%{q}%"),
                DMResource.resource_text.ilike(f"%{q}%"),
                DMResource.resource_url.ilike(f"%{q}%"),
                DMResource.category.ilike(f"%{q}%"),
                Reel.caption.ilike(f"%{q}%"),
                Reel.creator_name.ilike(f"%{q}%")
            )
        )
        .order_by(desc(DMResource.received_at))
        .limit(limit)
    )

    result = await db.execute(stmt)
    resources = list(result.scalars().all())

    return APIResponse(data=resources, meta=None)
