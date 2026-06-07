from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.process_log import ProcessLog
from app.schemas.log import ProcessLogResponse
from app.schemas.common import APIResponse, PaginationMeta
from uuid import UUID
from typing import List, Optional

router = APIRouter(prefix="/logs", tags=["Process Logs"])

@router.get("", response_model=APIResponse[List[ProcessLogResponse]])
async def list_logs(
    page: int = 1,
    per_page: int = 15,
    reel_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    step_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all execution logs for monitoring automation worker steps.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 15

    offset = (page - 1) * per_page
    
    query = select(ProcessLog)
    count_query = select(func.count(ProcessLog.id))
    
    if reel_id:
        query = query.where(ProcessLog.reel_id == reel_id)
        count_query = count_query.where(ProcessLog.reel_id == reel_id)
        
    if status_filter:
        query = query.where(ProcessLog.status == status_filter)
        count_query = count_query.where(ProcessLog.status == status_filter)
        
    if step_name:
        query = query.where(ProcessLog.step_name == step_name)
        count_query = count_query.where(ProcessLog.step_name == step_name)

    # Newest logs first
    query = query.order_by(desc(ProcessLog.timestamp)).offset(offset).limit(per_page)
    
    # Count total
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Get results
    results_res = await db.execute(query)
    logs = list(results_res.scalars().all())
    
    total_pages = (total + per_page - 1) // per_page
    
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return APIResponse(data=logs, meta=meta)
