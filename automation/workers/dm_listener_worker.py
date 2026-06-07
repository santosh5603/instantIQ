"""
DM Listener Worker — Polls the Instagram inbox via instagrapi and enqueues
discovered Reels to the RQ reel_queue.

Replaces the Playwright-based inbox scanning (which launched a full browser,
navigated to /direct/inbox/, clicked threads, and scrolled) with a single
instagrapi API call.
"""

import json
import logging
import uuid
import random
import time
import sys
import os
from datetime import datetime
from pathlib import Path

from redis import Redis
from rq import Queue

# Setup paths
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent
backend_dir = project_root.parent / "backend"
if not backend_dir.exists() and Path("/app/backend").exists():
    backend_dir = Path("/app/backend")
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(worker_dir))

from config import settings
from instagram.session import get_instagrapi_client, reset_client
from instagram.dm_reader import scan_inbox_for_reels

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dm_listener_worker")

# Database imports for saving discovered reels
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.models.reel import Reel
from app.models.process_log import ProcessLog


def _get_db_engine():
    """Create a synchronous SQLAlchemy engine for the DM listener worker."""
    db_url = settings.DATABASE_URL
    # Convert async URL schemes to sync psycopg2
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "?ssl=require" in db_url:
        # psycopg2 uses sslmode=require
        db_url = db_url.replace("?ssl=require", "?sslmode=require")
    return create_engine(db_url, pool_pre_ping=True)


def _get_db_session(engine) -> Session:
    """Create a new database session."""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


from instagram.dm_reader import extract_shortcode


def process_discovered_reels(discovered: list, redis_conn: Redis):
    """
    Save newly discovered Reels to the database and enqueue them for processing.
    """
    if not discovered:
        return

    engine = _get_db_engine()

    for item in discovered:
        url = item["reel_url"]
        sender = item["sender_username"]
        msg_id = item["message_id"]

        shortcode = extract_shortcode(url)
        if not shortcode:
            logger.warning(f"Could not extract shortcode from shared URL: {url}. Skipping.")
            continue

        normalized_url = f"https://www.instagram.com/reel/{shortcode}/"

        session = _get_db_session(engine)
        try:
            # Check if already exists in DB by searching for shortcode
            existing = session.execute(
                select(Reel).where(Reel.reel_url.like(f"%{shortcode}%"))
            ).scalar_one_or_none()

            if existing:
                # 1. If it's the exact same DM message ID, we have already processed this specific share!
                if existing.dm_message_id == msg_id:
                    logger.info(f"Reel {shortcode} already processed for DM message {msg_id} (status: '{existing.status}'). Skipping.")
                    continue

                # 2. If it's a new share message but the job is actively running, skip to avoid race conditions!
                if existing.status in ["processing", "waiting_dm", "awaiting_follow", "awaiting_comment"]:
                    logger.info(f"Reel {shortcode} shared again but is actively being processed (status: '{existing.status}'). Skipping to avoid race condition.")
                    continue

                # 3. Otherwise (it's a new DM share and old job is completed/failed), reset and re-process!
                logger.info(f"Reel {shortcode} shared again in new DM message {msg_id} (old message: {existing.dm_message_id}, status: '{existing.status}'). Resetting and re-queuing...")
                existing.dm_message_id = msg_id
                existing.status = "pending"
                existing.retry_count = 0
                existing.error_message = None
                existing.reel_url = normalized_url  # Auto-migrate to normalized format
                
                audit_log = ProcessLog(
                    reel_id=existing.id,
                    step_name="retry",
                    status="info",
                    message=f"Reel re-enqueued by DM inbox listener (detected new DM share message {msg_id})."
                )
                session.add(audit_log)
                session.commit()

                # Enqueue to RQ reel_queue
                reel_q = Queue("reelise:reel_queue", connection=redis_conn, default_timeout=900)
                job_id = str(uuid.uuid4())
                job_data = {
                    "job_id": job_id,
                    "reel_id": str(existing.id),
                    "job_type": "process_reel",
                    "payload": {"reel_url": normalized_url},
                    "attempt": 1,
                    "max_attempts": 3,
                    "created_at": datetime.utcnow().isoformat(),
                }
                reel_q.enqueue("workers.reel_worker.process_reel_task_sync", job_data, job_id=job_id)
                logger.info(f"Re-queued process_reel job for reel ID {existing.id} via python-rq")
                continue

            # Create new Reel record
            new_reel = Reel(
                reel_url=normalized_url,
                creator_name=None,  # Will be extracted by reel worker
                status="pending",
                dm_message_id=msg_id
            )
            session.add(new_reel)
            session.flush()  # Get the ID

            # Add process audit log
            audit_log = ProcessLog(
                reel_id=new_reel.id,
                step_name="discovery",
                status="success",
                message=f"Discovered Reel URL from DM with @{sender} via instagrapi."
            )
            session.add(audit_log)
            session.commit()

            # Enqueue to RQ reel_queue
            reel_q = Queue("reelise:reel_queue", connection=redis_conn, default_timeout=900)
            job_id = str(uuid.uuid4())
            job_data = {
                "job_id": job_id,
                "reel_id": str(new_reel.id),
                "job_type": "process_reel",
                "payload": {"reel_url": normalized_url},
                "attempt": 1,
                "max_attempts": 3,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Enqueue using python-rq
            reel_q.enqueue("workers.reel_worker.process_reel_task_sync", job_data, job_id=job_id)
            logger.info(f"Queued process_reel job for reel ID {new_reel.id} via python-rq")

        except Exception as e:
            logger.error(f"Error processing discovered reel {url}: {e}")
            session.rollback()
        finally:
            session.close()

    engine.dispose()


def run_listener_cycle(redis_conn: Redis):
    """Execute a single inbox scan cycle using instagrapi."""
    logger.info("Starting DM inbox scan cycle (instagrapi)...")

    try:
        cl = get_instagrapi_client()
    except Exception as e:
        logger.critical(f"Failed to get instagrapi client: {e}")
        reset_client()
        return

    admin_username = settings.INSTAGRAM_ADMIN_USERNAME

    try:
        discovered = scan_inbox_for_reels(cl, admin_username)
    except Exception as e:
        logger.error(f"Error during inbox scan: {e}")
        # Reset client in case of session issues
        reset_client()
        return

    if discovered:
        logger.info(f"Discovered {len(discovered)} Reel URL(s). Processing...")
        process_discovered_reels(discovered, redis_conn)
    else:
        logger.info("No new shared Reel URLs discovered in this cycle.")


def main():
    logger.info("Instagram DM Inbox Listener (instagrapi) is now ONLINE.")

    redis_conn = Redis.from_url(settings.REDIS_URL)

    while True:
        try:
            run_listener_cycle(redis_conn)
        except Exception as cycle_err:
            logger.error(f"Error in DM listener cycle: {cycle_err}")

        # Poll interval spacing
        poll_min = getattr(settings, "DM_POLL_INTERVAL_MIN", 5) * 60
        poll_max = getattr(settings, "DM_POLL_INTERVAL_MAX", 15) * 60
        sleep_seconds = random.randint(poll_min, poll_max)

        logger.info(f"Cycle complete. Sleeping for {sleep_seconds // 60} minutes...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
