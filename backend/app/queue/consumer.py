import json
from datetime import datetime
from app.queue.client import get_redis_client
from app.queue.constants import QueueNames

async def pop_job(queue_name: str, timeout: int = 30) -> dict | None:
    """Performs a blocking pop operation (BRPOP) to pull tasks safely without polling."""
    redis = await get_redis_client()
    result = await redis.brpop(queue_name, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)

async def push_to_dead_letter(job: dict, error: str) -> None:
    """Moves an unrecoverable job task to the dead_letter_queue in Redis."""
    redis = await get_redis_client()
    job["dead_letter_reason"] = error
    job["dead_letter_at"] = datetime.utcnow().isoformat()
    await redis.lpush(QueueNames.DEAD_LETTER, json.dumps(job))
