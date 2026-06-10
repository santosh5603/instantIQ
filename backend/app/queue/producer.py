import json
import uuid
from datetime import datetime
from app.queue.client import get_redis_client
from app.queue.constants import QueueNames
from app.config import settings
from rq import Queue
from redis import Redis

async def push_reel_job(reel_id: str, reel_url: str) -> str:
    """Pushes a new process reel task to the active Redis reel_queue via python-rq."""
    conn = Redis.from_url(settings.REDIS_URL)
    q = Queue(QueueNames.REEL, connection=conn, default_timeout=900)
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "reel_id": reel_id,
        "job_type": "process_reel",
        "payload": {"reel_url": reel_url},
        "attempt": 1,
        "max_attempts": 3,
        "created_at": datetime.utcnow().isoformat(),
    }
    q.enqueue("workers.reel_worker.process_reel_task_sync", job_data, job_id=job_id)
    return job_id

async def push_notion_sync_job(reel_id: str, resource_id: str) -> str:
    """Pushes a notion database sync task to the notion_sync_queue via python-rq."""
    conn = Redis.from_url(settings.REDIS_URL)
    q = Queue(QueueNames.NOTION_SYNC, connection=conn, default_timeout=600)
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "reel_id": reel_id,
        "resource_id": resource_id,
        "job_type": "notion_sync",
        "attempt": 1,
        "max_attempts": 3,
        "created_at": datetime.utcnow().isoformat(),
    }
    q.enqueue("workers.notion_sync_worker.process_sync_task_sync", job_data, job_id=job_id)
    return job_id

async def get_queue_depths() -> dict:
    """Returns the depth metrics for all active Redis queues via python-rq."""
    conn = Redis.from_url(settings.REDIS_URL)
    reel_q = Queue(QueueNames.REEL, connection=conn)
    notion_q = Queue(QueueNames.NOTION_SYNC, connection=conn)
    return {
        "reel_queue":        len(reel_q),
        "comment_queue":     0,
        "resource_queue":    0,
        "notion_sync_queue": len(notion_q),
        "retry_queue":       0,
        "dead_letter_queue": 0,
    }


class QueueProducer:
    async def enqueue_reel_job(self, reel_id, reel_url: str) -> bool:
        try:
            await push_reel_job(str(reel_id), reel_url)
            return True
        except Exception as e:
            import logging
            logging.getLogger("queue_producer").error(f"Error enqueuing reel job: {e}")
            return False

    async def enqueue_notion_sync_job(self, reel_id, resource_id) -> bool:
        try:
            await push_notion_sync_job(str(reel_id), str(resource_id))
            return True
        except Exception as e:
            import logging
            logging.getLogger("queue_producer").error(f"Error enqueuing notion sync job: {e}")
            return False

queue_producer = QueueProducer()

