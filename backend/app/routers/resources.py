from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.dm_resource import DMResource
from app.models.reel import Reel
from app.models.process_log import ProcessLog
from app.schemas.resource import ResourceResponse, ResourceUpdate
from app.schemas.common import APIResponse, PaginationMeta
from app.services.notion_service import notion_service
from uuid import UUID
from typing import List, Optional
import logging

logger = logging.getLogger("resources_router")
router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("", response_model=APIResponse[List[ResourceResponse]])
async def list_resources(
    page: int = 1,
    per_page: int = 10,
    category: Optional[str] = None,
    notion_synced: Optional[bool] = None,
    reel_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all harvested DM resources with paginated and filtered queries.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10

    offset = (page - 1) * per_page
    
    # Build queries
    query = select(DMResource)
    count_query = select(func.count(DMResource.id))
    
    if category:
        query = query.where(DMResource.category == category)
        count_query = count_query.where(DMResource.category == category)
        
    if notion_synced is not None:
        query = query.where(DMResource.notion_synced == notion_synced)
        count_query = count_query.where(DMResource.notion_synced == notion_synced)
        
    if reel_id:
        query = query.where(DMResource.reel_id == reel_id)
        count_query = count_query.where(DMResource.reel_id == reel_id)

    query = query.order_by(desc(DMResource.received_at)).offset(offset).limit(per_page)
    
    # Count total
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Fetch results
    results_res = await db.execute(query)
    resources = list(results_res.scalars().all())
    
    total_pages = (total + per_page - 1) // per_page
    
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
    
    return APIResponse(data=resources, meta=meta)

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get detailed metrics of a single harvested resource.
    """
    stmt = select(DMResource).where(DMResource.id == resource_id)
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )
    return resource

@router.patch("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: UUID, 
    payload: ResourceUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update category tag or manual sync status on a harvested resource.
    """
    stmt = select(DMResource).where(DMResource.id == resource_id)
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )

    if payload.category is not None:
        resource.category = payload.category
        
    if payload.notion_synced is not None:
        resource.notion_synced = payload.notion_synced

    # Record log
    audit_log = ProcessLog(
        reel_id=resource.reel_id,
        step_name="resource_update",
        status="info",
        message=f"Resource {resource.id} details updated via API."
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(resource)
    return resource

@router.post("/{resource_id}/sync", response_model=ResourceResponse)
async def sync_resource_to_notion(resource_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually force synchronization of a single DM Resource to the Notion Dashboard.
    """
    # Fetch resource and its parent reel
    stmt = select(DMResource).where(DMResource.id == resource_id)
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found."
        )

    stmt_reel = select(Reel).where(Reel.id == resource.reel_id)
    reel_res = await db.execute(stmt_reel)
    reel = reel_res.scalar_one_or_none()

    if not reel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated Reel not found."
        )

    # Trigger Notion Sync
    success, notion_page_id, error_msg = await notion_service.sync_resource(reel, resource)
    
    if success:
        resource.notion_synced = True
        resource.notion_page_id = notion_page_id
        
        audit_log = ProcessLog(
            reel_id=reel.id,
            step_name="notion_sync",
            status="success",
            message=f"Resource successfully synced to Notion page {notion_page_id}."
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(resource)
        return resource
    else:
        audit_log = ProcessLog(
            reel_id=reel.id,
            step_name="notion_sync",
            status="error",
            error_message=error_msg,
            message="Manual sync to Notion failed."
        )
        db.add(audit_log)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Notion API Sync failed: {error_msg}"
        )
