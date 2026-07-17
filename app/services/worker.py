import time
from datetime import datetime, timezone

from app.models.job import JobState
from app.repositories.job import JobRepository
from app.services.queue import QueueService
from app.services.retry import RetryService
from app.workers.executor import CommandExecutor


class WorkerService:

    def __init__(
        self,
        repository: JobRepository,
        queue: QueueService,
    ):
        self.repository = repository
        self.queue = queue
        self.executor = CommandExecutor()

    def start(self):

        while True:

            job_id = self.queue.dequeue()

            if job_id:
                self._process(job_id)

            # Poll for retryable jobs (failed jobs whose retry time has come)
            retryable_jobs = self.repository.get_retryable_jobs()
            for job in retryable_jobs:
                self.queue.enqueue(job.id, job.priority)
                job.next_retry_at = None
                self.repository.update(job)

            # Poll for scheduled jobs (run_at has arrived)
            scheduled_jobs = self.repository.get_scheduled_jobs()
            for job in scheduled_jobs:
                self.queue.enqueue(job.id, job.priority)
                # Clear run_at so we don't re-enqueue
                job.run_at = None
                self.repository.update(job)

            time.sleep(1)

    def _process(self, job_id: str):

        job = self.repository.get_by_id(job_id)

        if not job:
            return

        # Mark as processing with start time
        job.state = JobState.PROCESSING
        job.started_at = datetime.utcnow()
        self.repository.update(job)

        # Execute with optional timeout
        result = self.executor.execute(job.command, timeout=job.timeout)

        # Record end time and duration
        job.completed_at = datetime.utcnow()
        if job.started_at:
            delta = job.completed_at - job.started_at
            job.duration_ms = int(delta.total_seconds() * 1000)

        # Save output logs
        job.stdout = result.stdout if result.stdout else None
        job.stderr = result.stderr if result.stderr else None

        if result.timed_out:
            job.state = JobState.TIMED_OUT
            job.last_error = result.stderr
        elif result.returncode == 0:
            job.state = JobState.COMPLETED
        else:
            job.attempts += 1
            job.last_error = result.stderr

            if job.attempts >= job.max_retries:
                job.state = JobState.DEAD
            else:
                job.state = JobState.PENDING
                job.next_retry_at = RetryService().next_retry(job.attempts)

        self.repository.update(job)

        print(f"Job {job.id} finished with state {job.state.value}")