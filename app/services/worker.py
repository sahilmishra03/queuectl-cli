import signal
import sys
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
        self._shutdown_flag = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        print(f"\nReceived signal {signum}. Initiating graceful shutdown...")
        self._shutdown_flag = True


    def start(self):

        while not self._shutdown_flag:

            job_id = self.queue.dequeue()

            if job_id:
                self._process(job_id)

            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            print(f"[{now_utc}] Checking retryable jobs...")
            retryable_jobs = self.repository.get_retryable_jobs()
            print(f"[{now_utc}] Found {len(retryable_jobs)} retryable jobs")

            for job in retryable_jobs:
                self.queue.enqueue(job.id)
                # Reset next_retry_at so we don't enqueue the same job multiple times
                job.next_retry_at = None
                self.repository.update(job)

            time.sleep(1)

    def _process(self, job_id: str):

        job = self.repository.get_by_id_for_update(job_id)

        if not job:
            return

        if job.state != JobState.PENDING:
            print(f"Job {job.id} is not in PENDING state (current state: {job.state.value}). Skipping duplicate processing.")
            return

        job.state = JobState.PROCESSING
        self.repository.update(job)

        result = self.executor.execute(job.command)

        if result.returncode == 0:
            job.state = JobState.COMPLETED
        else:
            job.attempts += 1
            job.last_error = result.stderr

            if job.attempts >= job.max_retries:
                job.state = JobState.DEAD
            else:
                job.state = JobState.PENDING
                job.next_retry_at = RetryService().next_retry(job.attempts)
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                print(f"[{now_utc}] Next retry at: {job.next_retry_at}")

        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            print(result.stderr, end="")

        self.repository.update(job)

        print(
            f"Job {job.id} finished with state {job.state.value}"
        )