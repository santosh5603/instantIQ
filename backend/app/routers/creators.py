from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.creator_relationship import CreatorRelationship
from app.schemas.creator import CreatorResponse
from app.schemas.common import APIResponse, PaginationMeta
from uuid import UUID
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/creators", tags=["Creators"])

@router.get("", response_model=APIResponse[List[CreatorResponse]])
async def list_creators(
    page: int = 1,
    per_page: int = 10,
    followed_only: Optional[bool] = None,
    creator_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List tracked creators and relationship status.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10

    offset = (page - 1) * per_page
    
    query = select(CreatorRelationship)
    count_query = select(func.count(CreatorRelationship.id))
    
    if followed_only is not None:
        query = query.where(CreatorRelationship.followed == followed_only)
        count_query = count_query.where(CreatorRelationship.followed == followed_only)
        
    if creator_name:
        query = query.where(CreatorRelationship.creator_name.ilike(f"%{creator_name}%"))
        count_query = count_query.where(CreatorRelationship.creator_name.ilike(f"%{creator_name}%"))

    query = query.order_by(desc(CreatorRelationship.updated_at)).offset(offset).limit(per_page)
    
    # Count total
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Get results
    results_res = await db.execute(query)
    creators = list(results_res.scalars().all())
    
    total_pages = (total + per_page - 1) // per_page
    
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return APIResponse(data=creators, meta=meta)

@router.get("/{creator_id}", response_model=CreatorResponse)
async def get_creator(creator_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get detailed interaction history and status of a single creator.
    """
    stmt = select(CreatorRelationship).where(CreatorRelationship.id == creator_id)
    result = await db.execute(stmt)
    creator = result.scalar_one_or_none()
    
    if not creator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator relationship not found."
        )
    return creator

@router.post("/{creator_id}/unfollow", response_model=CreatorResponse)
async def mark_unfollowed(creator_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually mark a creator relationship as unfollowed.
    """
    stmt = select(CreatorRelationship).where(CreatorRelationship.id == creator_id)
    result = await db.execute(stmt)
    creator = result.scalar_one_or_none()
    
    if not creator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator relationship not found."
        )
        
    creator.followed = False
    creator.unfollowed_at = datetime.utcnow()
    creator.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(creator)
    return creator
