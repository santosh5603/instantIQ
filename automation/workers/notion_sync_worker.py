import asyncio
import json
import logging
import sys
import os
import uuid
from datetime import datetime
from pathlib import Path

# Dynamically add paths for module loading (both local and backend)
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent.parent
backend_dir = project_root / "backend"
if not backend_dir.exists() and Path("/app/backend").exists():
    backend_dir = Path("/app/backend")
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(worker_dir.parent))
sys.path.insert(0, str(worker_dir))

from base_worker import get_worker_db, redis_client

# Import shared models and services from backend
from app.models.reel import Reel
from app.models.dm_resource import DMResource
from app.models.process_log import ProcessLog
from app.services.notion_service import notion_service

logger = logging.getLogger("notion_sync_worker")

async def log_step(db, reel_id: uuid.UUID, step_name: str, status: str, message: str, error_message: str = None):
    """Utility helper to write audit process logs."""
    log = ProcessLog(
        reel_id=reel_id,
        step_name=step_name,
        status=status,
        message=message,
        error_message=error_message
    )
    db.add(log)
    await db.commit()

async def process_sync_task(job_data: dict):
    """
    Core sync processor calling Notion APIs and mapping harvested resources.
    """
    reel_id = job_data["reel_id"]
    resource_id = job_data["resource_id"]
    
    logger.info(f"Processing Notion Sync Job: ReelID={reel_id}, ResourceID={resource_id}")
    
    async with get_worker_db() as db:
        from sqlalchemy import select
        
        # 1. Fetch DM Resource
        stmt_res = select(DMResource).where(DMResource.id == uuid.UUID(resource_id))
        res_db = await db.execute(stmt_res)
        resource = res_db.scalar_one_or_none()
        
        if not resource:
            logger.error(f"DMResource {resource_id} not found in database. Aborting sync.")
            return
            
        # 2. Fetch Parent Reel
        stmt_reel = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_db = await db.execute(stmt_reel)
        reel = reel_db.scalar_one_or_none()
        
        if not reel:
            logger.error(f"Associated Reel {reel_id} not found in database. Aborting sync.")
            return

        # 3. Call Notion Sync Service
        logger.info(f"Syncing resource {resource.id} to Notion...")
        success, notion_page_id, error_msg = await notion_service.sync_resource(reel, resource)
        
        # Refetch inside a fresh session if needed, but since we are within context:
        if success:
            resource.notion_synced = True
            resource.notion_page_id = notion_page_id
            
            # Check if all resources for this reel are now synced
            # (Optional, but useful to flag Reel)
            reel.notion_synced = True
            reel.notion_page_id = notion_page_id
            
            await db.commit()
            await log_step(
                db, 
                reel.id, 
                "notion_sync", 
                "success", 
                f"Successfully synchronized resource to Notion page: '{notion_page_id}'."
            )
            logger.info(f"SUCCESS: Synchronized resource {resource.id} to Notion page {notion_page_id}")
        else:
            await log_step(
                db, 
                reel.id, 
                "notion_sync", 
                "error", 
                f"Failed to synchronize resource to Notion.", 
                error_msg
            )
            logger.error(f"FAILED: Sync of resource {resource.id} to Notion failed: {error_msg}")

def process_sync_task_sync(job_data: dict):
    """Synchronous wrapper for python-rq worker execution."""
    asyncio.run(process_sync_task(job_data))


def main():
    from rq import Worker, Queue
    from redis import Redis
    from config import settings
    import socket
    import os
    import uuid
    conn = Redis.from_url(settings.REDIS_URL)
    q = Queue("reelise:notion_sync_queue", connection=conn)
    worker_name = f"notion-sync-worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    worker = Worker([q], connection=conn, name=worker_name)
    logger.info(f"Starting RQ Worker '{worker_name}' for reelise:notion_sync_queue...")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    main()
