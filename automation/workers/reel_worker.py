"""
Reel Worker — Processes reel extraction, follow, comment, and DM harvest pipeline.

HYBRID ARCHITECTURE:
- Playwright: ONLY for caption extraction (reel_extractor.py) — requires a browser
- instagrapi: For everything else — follow, comment, DM harvest, session management

Consumes jobs from the Redis reel_queue via BRPOP (compatible with both raw
Redis push and RQ enqueue patterns).
"""

import asyncio
import json
import logging
import sys
import os
import uuid
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Setup paths
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent.parent
backend_dir = project_root / "backend"
if not backend_dir.exists() and Path("/app/backend").exists():
    backend_dir = Path("/app/backend")
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(worker_dir.parent))
sys.path.insert(0, str(worker_dir))

from base_worker import get_worker_db, redis_client
from config import settings

# Playwright modules (ONLY for caption extraction)
from playwright_custom.instagram.session import create_instagram_context, is_session_valid
from playwright_custom.instagram.reel_extractor import extract_reel_metadata

# instagrapi modules (for follow, comment, DM harvest)
from instagram.session import get_instagrapi_client, reset_client
from instagram.follow_agent import follow_creator as insta_follow_creator, is_following_creator
from instagram.comment_agent import post_comment as insta_post_comment
from instagram.dm_harvester import (
    harvest_dm_resources as insta_harvest_dm,
    check_follow_required_in_dm,
    harvest_dm_resources_and_buttons
)
from instagram.cta_detector import detect_cta_from_comments
from instagram.utils import async_random_sleep

# Pure Python utilities (no Playwright dependency)
from playwright_custom.utils.cta_detector import detect_cta

# Import shared models and services from backend
from app.models.reel import Reel
from app.models.dm_resource import DMResource
from app.models.process_log import ProcessLog
from app.models.creator_relationship import CreatorRelationship
from app.services.supabase_service import supabase_service

logger = logging.getLogger("reel_worker")


async def log_step(db, reel_id: str, step_name: str, status: str, message: str, error_message: str = None):
    """Utility helper to write audit process logs."""
    log = ProcessLog(
        reel_id=uuid.UUID(reel_id),
        step_name=step_name,
        status=status,
        message=message,
        error_message=error_message
    )
    db.add(log)
    await db.commit()


async def extract_caption_with_playwright(reel_url: str):
    """
    The ONLY Playwright usage in the entire system.
    Opens a reel URL in a headless browser and extracts creator name + caption.

    Returns:
        Tuple[creator_name, caption] or (None, None) on failure.
    """
    logger.info(f"[Playwright] Extracting caption from: {reel_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        context = await create_instagram_context(browser)
        page = await context.new_page()

        try:
            # Verify Playwright session
            if not await is_session_valid(page):
                logger.error("[Playwright] Session invalid. Caption extraction requires a valid browser session.")
                return None, None

            # Extract metadata
            creator_name, caption = await extract_reel_metadata(page, reel_url)
            return creator_name, caption

        except Exception as e:
            logger.error(f"[Playwright] Caption extraction failed: {e}")
            return None, None
        finally:
            await context.close()
            await browser.close()


async def handle_failure(reel_id: str, error_msg: str, step_name: str, status: str, job_data: dict):
    """
    Atomic retry mechanism:
    - Increments the retry_count of the Reel in the database.
    - If retry_count < 3: sets status to 'pending' (or 'retrying'), logs the failure context,
      sleeps for 60 seconds, and re-enqueues the job to reelise:reel_queue.
    - If retry_count >= 3: marks the Reel as permanently failed, logs the abort.
    """
    logger.warning(f"Job failed at step '{step_name}': {error_msg}. Starting retry evaluation...")
    from sqlalchemy import select

    async with get_worker_db() as db:
        stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_res = await db.execute(stmt)
        reel = reel_res.scalar_one_or_none()

        if not reel:
            logger.error(f"Reel {reel_id} not found during failure handling.")
            return

        current_retries = reel.retry_count if reel.retry_count is not None else 0
        new_retries = current_retries + 1
        reel.retry_count = new_retries
        reel.error_message = error_msg

        if new_retries < 3:
            reel.status = "pending" # Keep as pending so worker picker finds it cleanly on retry
            await db.commit()
            
            await log_step(
                db, 
                reel_id, 
                step_name, 
                "retry", 
                f"Step failed. Scheduling retry {new_retries}/3. Sleeping 60s before re-enqueue...", 
                error_msg
            )
            
            logger.info(f"Sleeping 60 seconds before re-enqueuing job {job_data.get('job_id')}...")
            await asyncio.sleep(60.0)
            
            # Re-enqueue the job using a new job ID
            from rq import Queue
            from redis import Redis
            conn = Redis.from_url(settings.REDIS_URL)
            q = Queue("reelise:reel_queue", connection=conn, default_timeout=900)
            
            new_job_id = str(uuid.uuid4())
            new_job_data = job_data.copy()
            new_job_data["job_id"] = new_job_id
            new_job_data["attempt"] = new_retries + 1
            
            q.enqueue("workers.reel_worker.process_reel_task_sync", new_job_data, job_id=new_job_id)
            logger.info(f"Successfully re-enqueued job to reelise:reel_queue with new job_id={new_job_id}")
        else:
            reel.status = status if status in ["failed", "dm_timeout"] else "failed"
            await db.commit()
            await log_step(
                db, 
                reel_id, 
                step_name, 
                "error", 
                f"Job permanently failed after 3 attempts.", 
                error_msg
            )
            logger.error(f"Job permanently failed after 3 attempts: {error_msg}")


async def process_reel_task(job_data: dict):
    """
    Core pipeline controller:
    1. Initialize instagrapi client & sync Playwright session
    2. Caption extraction (Playwright)
    3. CTA parsing (pure Python)
    4. State Verification & Sync (instagrapi)
    5. Follow creator (instagrapi)
    6. Post comment (instagrapi)
    7. Harvest DM resources (instagrapi + simulated button click handling)
    8. Queue Notion sync
    """
    reel_id = job_data["reel_id"]
    reel_url = job_data["payload"]["reel_url"]

    logger.info(f"Processing Reel Job: ID={reel_id}, URL={reel_url}")

    from sqlalchemy import select

    # Update status to processing
    async with get_worker_db() as db:
        stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_res = await db.execute(stmt)
        reel = reel_res.scalar_one_or_none()

        if not reel:
            logger.error(f"Reel {reel_id} not found in database.")
            return

        if reel.retry_count is None:
            reel.retry_count = 0
            await db.commit()

        reel.status = "processing"
        await db.commit()
        await log_step(db, reel_id, "verification", "info", f"Started processing job. Attempt {reel.retry_count + 1}/3...")

    # ---- STEP 1: INITIALIZE INSTAGRAPI & SYNC PLAYWRIGHT ----
    # We initialize instagrapi at the very beginning to perform login and sync cookies to Playwright
    try:
        cl = get_instagrapi_client()
    except Exception as e:
        await handle_failure(
            reel_id=reel_id,
            error_msg=f"Failed to initialize instagrapi client or sync session to Playwright: {e}",
            step_name="authentication",
            status="failed",
            job_data=job_data
        )
        return

    # ---- STEP 2: Caption Extraction (PLAYWRIGHT) ----
    creator_name, caption = await extract_caption_with_playwright(reel_url)

    if not creator_name or not caption:
        await handle_failure(
            reel_id=reel_id,
            error_msg="Failed to extract caption or creator username from Reel page via Playwright.",
            step_name="extraction",
            status="failed",
            job_data=job_data
        )
        return

    # Save extracted metadata
    async with get_worker_db() as db:
        stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_res = await db.execute(stmt)
        reel = reel_res.scalar_one_or_none()
        reel.creator_name = creator_name
        reel.caption = caption
        await db.commit()
        await log_step(db, reel_id, "extraction", "success", f"Extracted Reel metadata. Creator: @{creator_name}.")

    # ---- STEP 3: CTA Detection ----
    cta_results = detect_cta(caption)
    logger.info(f"Caption CTA Parser results: {cta_results}")

    requires_comment = cta_results["requires_comment"]
    requires_follow = cta_results["requires_follow"]
    requires_dm = cta_results["requires_dm"]
    comment_keyword = cta_results["comment_keyword"]
    dm_keyword = cta_results["dm_keyword"]
    confidence = cta_results["confidence"]

    # If caption detection failed to find a comment keyword, fallback to comments-based CTA detection
    if not requires_comment or not comment_keyword:
        logger.info("Caption CTA detection did not resolve a comment keyword. Running comment-based detection...")
        loop = asyncio.get_event_loop()
        try:
            comment_keyword_found = await loop.run_in_executor(None, detect_cta_from_comments, cl, reel_url, creator_name)
            if comment_keyword_found:
                logger.info(f"Comments-based CTA detection found keyword: '{comment_keyword_found}'")
                requires_comment = True
                comment_keyword = comment_keyword_found
                confidence = 1.0
        except Exception as e:
            logger.warning(f"Comments-based CTA detection encountered an error: {e}")

    # Force follow creator if commenting is required
    if requires_comment:
        logger.info("Forcing requires_follow = True because commenting is required.")
        requires_follow = True

    async with get_worker_db() as db:
        stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_res = await db.execute(stmt)
        reel = reel_res.scalar_one_or_none()
        reel.requires_comment = requires_comment
        reel.requires_follow = requires_follow
        reel.requires_dm = requires_dm
        reel.comment_keyword = comment_keyword
        reel.dm_keyword = dm_keyword
        reel.cta_confidence = confidence

        if not requires_comment and not requires_dm:
            reel.status = "no_cta"
            await db.commit()
            await log_step(db, reel_id, "cta_detection", "warning",
                           "No CTA keywords found in caption or comments.")
            return

        await db.commit()
        await log_step(db, reel_id, "cta_detection", "success",
                       f"CTA detected. Comment: {requires_comment} ('{comment_keyword}'). Follow: {requires_follow}.")

    # ---- STEP 4: INSTAGRAM STATE VERIFICATION & SYNC ----
    # Ask Instagram directly for follow and comment status to prevent duplicate actions or overwrite outdated DB state
    logger.info(f"Verifying current Instagram state with @{creator_name}...")
    loop = asyncio.get_event_loop()

    # 4a. Verify follow status on Instagram
    is_following = False
    try:
        is_following = await loop.run_in_executor(None, is_following_creator, cl, creator_name)
        logger.info(f"Instagram reports follow status for @{creator_name}: {is_following}")
    except Exception as e:
        logger.warning(f"Could not check follow status on Instagram: {e}")

    # 4b. Verify comment status on Instagram
    has_commented = False
    if requires_comment and comment_keyword:
        try:
            media_pk = cl.media_pk_from_url(reel_url)
            media_id = cl.media_id(media_pk)
            comments = await loop.run_in_executor(None, lambda: cl.media_comments(media_id, amount=30))
            for c in comments:
                if c.user.username.lower() == cl.username.lower() and c.text.strip().upper() == comment_keyword.strip().upper():
                    has_commented = True
                    break
            logger.info(f"Instagram reports comment status: {has_commented}")
        except Exception as e:
            logger.warning(f"Could not check comment status on Instagram: {e}")

    # 4c. Sync status back to database
    async with get_worker_db() as db:
        stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
        reel_res = await db.execute(stmt)
        reel = reel_res.scalar_one_or_none()
        reel.followed = is_following
        if is_following and not reel.followed_at:
            reel.followed_at = datetime.utcnow()

        reel.commented = has_commented
        if has_commented and not reel.comment_posted_at:
            reel.comment_posted_at = datetime.utcnow()
        await db.commit()

    # ---- STEP 5: Follow Creator (INSTAGRAPI) ----
    if requires_follow and not is_following:
        async with get_worker_db() as db:
            stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
            reel_res = await db.execute(stmt)
            reel = reel_res.scalar_one_or_none()
            reel.status = "awaiting_follow"
            await db.commit()

        # Run sync instagrapi call in executor to avoid blocking the event loop
        followed_ok = await loop.run_in_executor(None, insta_follow_creator, cl, creator_name)

        if followed_ok:
            async with get_worker_db() as db:
                stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
                reel_res = await db.execute(stmt)
                reel = reel_res.scalar_one_or_none()
                reel.followed = True
                reel.followed_at = datetime.utcnow()

                # Update/Insert CreatorRelationship
                stmt_creator = select(CreatorRelationship).where(
                    CreatorRelationship.creator_name == creator_name
                )
                creator_res = await db.execute(stmt_creator)
                creator_rel = creator_res.scalar_one_or_none()

                if not creator_rel:
                    creator_rel = CreatorRelationship(
                        creator_name=creator_name,
                        followed=True,
                        followed_at=datetime.utcnow(),
                        purpose=reel_id,
                        total_reels=1
                    )
                    db.add(creator_rel)
                else:
                    creator_rel.followed = True
                    creator_rel.followed_at = datetime.utcnow()
                    creator_rel.total_reels += 1

                await db.commit()
                await log_step(db, reel_id, "follow_automation", "success",
                               f"Successfully followed @{creator_name} via instagrapi.")
        else:
            await handle_failure(
                reel_id=reel_id,
                error_msg=f"Failed or skipped follow on @{creator_name}.",
                step_name="follow_automation",
                status="failed",
                job_data=job_data
            )
            return

    # ---- STEP 6: Comment Automation (INSTAGRAPI) ----
    if requires_comment and comment_keyword and not has_commented:
        async with get_worker_db() as db:
            stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
            reel_res = await db.execute(stmt)
            reel = reel_res.scalar_one_or_none()
            reel.status = "awaiting_comment"
            await db.commit()

        commented_ok = await loop.run_in_executor(None, insta_post_comment, cl, reel_url, comment_keyword)

        if commented_ok:
            async with get_worker_db() as db:
                stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
                reel_res = await db.execute(stmt)
                reel = reel_res.scalar_one_or_none()
                reel.commented = True
                reel.comment_posted_at = datetime.utcnow()
                reel.status = "waiting_dm"
                await db.commit()
                await log_step(db, reel_id, "comment_automation", "success",
                               f"Posted comment '{comment_keyword}' via instagrapi.")
        else:
            await handle_failure(
                reel_id=reel_id,
                error_msg="Failed to post comment via instagrapi.",
                step_name="comment_automation",
                status="failed",
                job_data=job_data
            )
            return

    # ---- STEP 7: Wait & Harvest DM Resources (INSTAGRAPI with Interactive Button Tapping) ----
    resources = []
    button_texts = []
    thread_id = None
    
    max_dm_attempts = 5
    attempt_delay = 20.0
    button_tapped = False
    
    for attempt in range(1, max_dm_attempts + 1):
        logger.info(f"DM Harvest Attempt {attempt}/{max_dm_attempts} for @{creator_name}...")
        
        if attempt == 1:
            await async_random_sleep(15.0, 18.0)
        else:
            await async_random_sleep(attempt_delay, attempt_delay + 3.0)
            
        async with get_worker_db() as db:
            stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
            reel_res = await db.execute(stmt)
            reel = reel_res.scalar_one_or_none()
            reel.status = "waiting_dm"
            await db.commit()
            await log_step(db, reel_id, "dm_monitor", "info",
                           f"Checking DMs with @{creator_name} (Attempt {attempt}/{max_dm_attempts})...")

        # 7a. Harvest both raw links and potential card buttons
        resources, button_texts, thread_id = await loop.run_in_executor(
            None, harvest_dm_resources_and_buttons, cl, creator_name
        )
        
        if resources:
            logger.info(f"Resources found on attempt {attempt}!")
            break
            
        # 7b. Interactive postback button click handling
        if button_texts and not button_tapped and thread_id:
            button_text_to_tap = button_texts[0]
            logger.info(f"Interactive card buttons detected in thread: {button_texts}. Simulating tap on '{button_text_to_tap}'...")
            
            async with get_worker_db() as db:
                await log_step(db, reel_id, "dm_harvest", "info",
                               f"Found interactive button '{button_text_to_tap}' in DM. Sending tap simulation message...")
                               
            try:
                # Send the button text as a direct message reply to "tap" the button
                await loop.run_in_executor(
                    None, lambda: cl.direct_send(button_text_to_tap, thread_ids=[thread_id])
                )
                button_tapped = True
                logger.info("Simulated button tap reply sent successfully. Sleeping 15s to allow bot delivery...")
                await async_random_sleep(15.0, 18.0)
                
                # Immediately check DMs again after the simulated tap to harvest the delivered link
                logger.info("Rechecking DMs immediately after simulated button tap...")
                resources, _, _ = await loop.run_in_executor(
                    None, harvest_dm_resources_and_buttons, cl, creator_name
                )
                if resources:
                    break
            except Exception as send_err:
                logger.error(f"Failed to send simulated button tap: {send_err}")
            
        # 7c. Check if there is a follow-gate message in the thread
        logger.info("No resources found. Checking if creator thread has follow-gate prompt...")
        follow_required = await loop.run_in_executor(None, check_follow_required_in_dm, cl, creator_name)
        if follow_required:
            async with get_worker_db() as db:
                await log_step(db, reel_id, "dm_harvest", "info",
                               f"Follow-gate detected in DMs from @{creator_name}. Automatically following creator to unlock resource...")
            
            # Follow creator
            followed_ok = await loop.run_in_executor(None, insta_follow_creator, cl, creator_name)
            
            if followed_ok:
                async with get_worker_db() as db:
                    stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
                    reel_res = await db.execute(stmt)
                    reel = reel_res.scalar_one_or_none()
                    reel.followed = True
                    reel.followed_at = datetime.utcnow()
                    await db.commit()
                    await log_step(db, reel_id, "follow_automation", "success",
                                   f"Automatically followed @{creator_name} to bypass follow-gate.")
                
                # Wait 20 seconds for their bot to trigger delivery after follow
                logger.info("Waiting 20 seconds for creator bot to deliver link after follow...")
                await async_random_sleep(20.0, 23.0)
                
                # Re-harvest DMs
                logger.info("Re-checking DMs after following creator...")
                resources, _, _ = await loop.run_in_executor(
                    None, harvest_dm_resources_and_buttons, cl, creator_name
                )
                if resources:
                    break

    if resources:
        logger.info(f"Harvested {len(resources)} resource(s) from DM thread.")

        async with get_worker_db() as db:
            stmt = select(Reel).where(Reel.id == uuid.UUID(reel_id))
            reel_res = await db.execute(stmt)
            reel = reel_res.scalar_one_or_none()

            for res in resources:
                # Check if this resource URL is already saved for this reel to prevent duplicates
                from app.models.dm_resource import DMResource
                stmt_res = select(DMResource).where(
                    DMResource.reel_id == reel.id,
                    DMResource.resource_url == res["resource_url"]
                )
                res_check = await db.execute(stmt_res)
                if res_check.scalar_one_or_none():
                    logger.info(f"Resource {res['resource_url']} already harvested and saved. Skipping duplicate.")
                    continue

                new_resource = DMResource(
                    reel_id=reel.id,
                    resource_type=res["resource_type"],
                    resource_url=res["resource_url"],
                    resource_text=res["resource_text"],
                    category=res["category"],
                    file_name=res["file_name"],
                    notion_synced=False
                )
                db.add(new_resource)
                await db.flush()

                # Queue a Notion sync job using python-rq
                from rq import Queue
                from redis import Redis
                conn = Redis.from_url(settings.REDIS_URL)
                notion_q = Queue("reelise:notion_sync_queue", connection=conn, default_timeout=600)
                
                sync_job_id = str(uuid.uuid4())
                sync_job = {
                    "job_id": sync_job_id,
                    "reel_id": str(reel.id),
                    "resource_id": str(new_resource.id),
                    "job_type": "notion_sync",
                    "attempt": 1,
                    "max_attempts": 3,
                    "created_at": datetime.utcnow().isoformat(),
                }

                notion_q.enqueue("workers.notion_sync_worker.process_sync_task_sync", sync_job, job_id=sync_job_id)
                logger.info(f"Queued Notion Sync job for resource {new_resource.id} via python-rq")

            reel.status = "completed"
            reel.processed_at = datetime.utcnow()
            reel.error_message = None # Clear any previous error messages
            await db.commit()
            await log_step(db, reel_id, "dm_harvest", "success",
                           f"Harvested {len(resources)} DM resources. Queued for Notion sync.")
    else:
        await handle_failure(
            reel_id=reel_id,
            error_msg="No external resources received in DM thread after follow/comment/button-taps.",
            step_name="dm_harvest",
            status="dm_timeout",
            job_data=job_data
        )


def process_reel_task_sync(job_data: dict):
    """Synchronous wrapper for python-rq worker execution."""
    asyncio.run(process_reel_task(job_data))


def main():
    from rq import Worker, Queue
    from redis import Redis
    import socket
    import os
    import uuid
    conn = Redis.from_url(settings.REDIS_URL)
    q = Queue("reelise:reel_queue", connection=conn)
    worker_name = f"reel-worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    worker = Worker([q], connection=conn, name=worker_name)
    logger.info(f"Starting RQ Worker '{worker_name}' for reelise:reel_queue...")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    main()
