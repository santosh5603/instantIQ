"""
RQ Worker Entry Point — Processes jobs from reel_queue and notion_sync_queue.

Replaces the raw Redis BRPOP loops with python-rq managed workers.
This is the single process that handles all job execution.
"""

import sys
import os
import logging
from pathlib import Path
from redis import Redis
from rq import Worker, Queue

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rq_worker")

QUEUE_NAMES = [
    "reelise:reel_queue",
    "reelise:notion_sync_queue",
]


def main():
    redis_url = settings.REDIS_URL
    logger.info(f"Starting RQ Worker connecting to {redis_url}")
    logger.info(f"Listening on queues: {QUEUE_NAMES}")

    conn = Redis.from_url(redis_url)

    queues = [Queue(name, connection=conn) for name in QUEUE_NAMES]

    worker = Worker(queues, connection=conn, name="reelise-worker")

    logger.info("RQ Worker is now ONLINE and listening for jobs.")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
