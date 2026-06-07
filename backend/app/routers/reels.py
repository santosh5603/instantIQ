from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.reel import Reel
from app.models.process_log import ProcessLog
from app.schemas.reel import ReelCreate, ReelResponse
from app.schemas.common import APIResponse, PaginationMeta
from app.queue.producer import queue_producer
from uuid import UUID
from typing import List, Optional
import logging
from datetime import datetime

logger = logging.getLogger("reels_router")
router = APIRouter(prefix="/reels", tags=["Reels"])

@router.post("", response_model=ReelResponse, status_code=status.HTTP_201_CREATED)
async def submit_reel(payload: ReelCreate, db: AsyncSession = Depends(get_db)):
    """
    Submit a new Instagram Reel URL for extraction, follow automation, comment trigger, and DM harvest.
    """
    # Check if Reel already exists
    stmt = select(Reel).where(Reel.reel_url == payload.reel_url)
    existing_result = await db.execute(stmt)
    existing_reel = existing_result.scalar_one_or_none()
    
    if existing_reel:
        if existing_reel.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A reel with this URL has already been completed successfully."
            )
        
        # If the existing reel is failed or not completed, we reset its status and re-enqueue it!
        existing_reel.status = "pending"
        existing_reel.retry_count = 0
        existing_reel.error_message = None
        if payload.creator_name:
            existing_reel.creator_name = payload.creator_name
            
        audit_log = ProcessLog(
            reel=existing_reel,
            step_name="retry",
            status="info",
            message="Reel re-queued cleanly via submit API (detected previous incomplete submission)."
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(existing_reel)
        
        # Re-queue to Redis
        try:
            await queue_producer.enqueue_reel_job(existing_reel.id, existing_reel.reel_url)
        except Exception as e:
            logger.error(f"Redis enqueue exception for existing reel {existing_reel.id}: {str(e)}")
            
        return existing_reel

    # Create new reel record
    new_reel = Reel(
        reel_url=payload.reel_url,
        creator_name=payload.creator_name,
        status="pending"
    )
    
    db.add(new_reel)
    
    # Save a process log for audit log
    audit_log = ProcessLog(
        reel=new_reel,
        step_name="submission",
        status="success",
        message="Reel submitted successfully via API."
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(new_reel)

    # Push to Redis Queue
    try:
        queued = await queue_producer.enqueue_reel_job(new_reel.id, new_reel.reel_url)
        if not queued:
            logger.error(f"Failed to queue reel job to Redis for reel {new_reel.id}")
            # Update status to degraded/failed if queue fails? We can keep it pending and retry
    except Exception as e:
        logger.error(f"Redis enqueue exception for reel {new_reel.id}: {str(e)}")

    return new_reel

@router.get("", response_model=APIResponse[List[ReelResponse]])
async def list_reels(
    page: int = 1,
    per_page: int = 10,
    status_filter: Optional[str] = None,
    creator_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all submitted reels with pagination and filter support.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10

    offset = (page - 1) * per_page
    
    # Build query
    query = select(Reel)
    count_query = select(func.count(Reel.id))
    
    if status_filter:
        query = query.where(Reel.status == status_filter)
        count_query = count_query.where(Reel.status == status_filter)
        
    if creator_filter:
        query = query.where(Reel.creator_name.ilike(f"%{creator_filter}%"))
        count_query = count_query.where(Reel.creator_name.ilike(f"%{creator_filter}%"))

    # Order by newest
    query = query.order_by(desc(Reel.created_at)).offset(offset).limit(per_page)
    
    # Execute count
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Execute query
    results_res = await db.execute(query)
    reels = list(results_res.scalars().all())
    
    total_pages = (total + per_page - 1) // per_page
    
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return APIResponse(data=reels, meta=meta)

@router.get("/{reel_id}", response_model=ReelResponse)
async def get_reel(reel_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve full execution and status metrics for a single Reel.
    """
    stmt = select(Reel).where(Reel.id == reel_id)
    result = await db.execute(stmt)
    reel = result.scalar_one_or_none()
    
    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found."
        )
    return reel

@router.post("/{reel_id}/retry", response_model=ReelResponse)
async def retry_reel(reel_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger retry on a failed, timed-out, or stuck Reel extraction job.
    """
    stmt = select(Reel).where(Reel.id == reel_id)
    result = await db.execute(stmt)
    reel = result.scalar_one_or_none()
    
    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found."
        )

    # Update states
    reel.status = "pending"
    reel.retry_count += 1
    reel.error_message = None
    
    audit_log = ProcessLog(
        reel_id=reel.id,
        step_name="retry",
        status="info",
        message=f"Manual retry triggered. Incremented retry count to {reel.retry_count}."
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(reel)
    
    # Re-queue to Redis
    try:
        await queue_producer.enqueue_reel_job(reel.id, reel.reel_url)
    except Exception as e:
        logger.error(f"Redis enqueue exception during retry for reel {reel.id}: {str(e)}")
        
    return reel

@router.delete("/{reel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reel(reel_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a Reel record and all associated logs and harvested resources.
    """
    stmt = select(Reel).where(Reel.id == reel_id)
    result = await db.execute(stmt)
    reel = result.scalar_one_or_none()
    
    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel not found."
        )
        
    await db.delete(reel)
    await db.commit()
    return None
