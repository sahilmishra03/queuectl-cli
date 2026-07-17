from app.models.job import Job, JobState
from app.repositories.job import JobRepository
from app.services.queue import QueueService


class DLQService:
    def __init__(self, repository: JobRepository, queue: QueueService):
        self.repository = repository
        self.queue = queue

    def list_jobs(self) -> list[Job]:
        return self.repository.get_dead_jobs()

    def retry(self, job_id: str) -> Job:
        job = self.repository.get_by_id(job_id)
        if not job:
            raise ValueError("Job not found.")
        
        if job.state != JobState.DEAD:
            raise ValueError("Job is not in dead letter queue.")

        updated_job = self.repository.reset_dead_job(job)
        self.queue.enqueue(updated_job.id)
        return updated_job
