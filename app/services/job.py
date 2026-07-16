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
    ) -> Job:

        job = Job(
            command=command,
            max_retries=max_retries,
        )

        self.repository.create(job)

        self.queue.enqueue(job.id)

        return job