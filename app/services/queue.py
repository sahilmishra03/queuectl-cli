from redis import Redis

from app.db.redis import redis_client


class QueueService:
    QUEUE_KEY = "queue:jobs"

    def __init__(self, redis: Redis = redis_client):
        self.redis = redis

    def enqueue(self, job_id: str, priority: int = 0) -> None:
        # Lower score = higher priority (dequeued first)
        score = -priority
        self.redis.zadd(self.QUEUE_KEY, {job_id: score})

    def dequeue(self) -> str | None:
        # ZPOPMIN returns the member with the lowest score (highest priority)
        result = self.redis.zpopmin(self.QUEUE_KEY, count=1)
        if result:
            member, _score = result[0]
            return member
        return None

    def size(self) -> int:
        return self.redis.zcard(self.QUEUE_KEY)