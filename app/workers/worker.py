from app.models.job import JobState
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


    def process(self):

        job_id = self.queue.dequeue()

        if not job_id:
            return None

        job = self.repository.get_by_id(job_id)

        if not job:
            return None

        job.state = JobState.PROCESSING
        self.repository.update(job)

        success = self.executor.execute(job.command)

        if success:
            job.state = JobState.COMPLETED
        else:
            job.state = JobState.FAILED

        self.repository.update(job)

        return job