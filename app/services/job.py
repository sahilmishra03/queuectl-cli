from datetime import datetime
from typing import Optional

from app.models.job import Job
from app.repositories.job import JobRepository
from app.services.queue import QueueService


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        queue: QueueService,
    ):
        self.repository = repository
        self.queue = queue

    def enqueue(
        self,
        command: str,
        max_retries: int = 3,
        priority: int = 0,
        timeout: Optional[int] = None,
        run_at: Optional[datetime] = None,
    ) -> Job:

        job = Job(
            command=command,
            max_retries=max_retries,
            priority=priority,
            timeout=timeout,
            run_at=run_at,
        )

        self.repository.create(job)

        # If run_at is set, don't enqueue now — worker will pick it up when ready
        if run_at is None:
            self.queue.enqueue(job.id, priority)

        return job