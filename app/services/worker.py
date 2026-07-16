from app.models.job import JobState
import time

from app.repositories.job import JobRepository
from app.services.queue import QueueService
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

            if not job_id:
                break

            job = self.repository.get_by_id(job_id)

            if not job:
                continue

            job.state = JobState.PROCESSING
            self.repository.update(job)

            result = self.executor.execute(job.command)

            if result.returncode == 0:
                job.state = JobState.COMPLETED
            else:
                job.state = JobState.FAILED

            if result.stdout:
                print(result.stdout, end="")

            if result.stderr:
                print(result.stderr, end="")

            self.repository.update(job)

            print(
                f"Job {job.id} finished with state {job.state.value}"
            )