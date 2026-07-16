from redis import Redis

from app.db.redis import redis_client


class QueueService:
    def __init__(self, redis: Redis = redis_client):
        self.redis = redis

    def enqueue(self, job_id: str) -> None:
        self.redis.rpush("queue:jobs", job_id)

    def dequeue(self) -> str | None:
        return self.redis.lpop("queue:jobs")

    def size(self) -> int:
        return self.redis.llen("queue:jobs")