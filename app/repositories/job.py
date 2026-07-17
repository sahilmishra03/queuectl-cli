from __future__ import annotations

from datetime import datetime
from sqlalchemy import or_, select

from app.models.job import Job, JobState
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository):

    def create(self, job: Job) -> Job:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: str) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        return self.db.scalar(stmt)

    def list(self) -> list[Job]:
        stmt = select(Job)
        return list(self.db.scalars(stmt))

    def update(self, job: Job) -> Job:
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_retryable_jobs(self) -> list[Job]:
        stmt = (
            select(Job)
            .where(Job.state == JobState.PENDING)
            .where(Job.next_retry_at.is_not(None))
            .where(Job.next_retry_at <= datetime.utcnow())
        )
        return list(self.db.scalars(stmt))

    def delete(self, job: Job) -> None:
        self.db.delete(job)
        self.db.commit()

    def get_dead_jobs(self) -> list[Job]:
        stmt = select(Job).where(Job.state == JobState.DEAD)
        return list(self.db.scalars(stmt))

    def reset_dead_job(self, job: Job) -> Job:
        job.state = JobState.PENDING
        job.attempts = 0
        job.next_retry_at = None
        job.last_error = None
        self.db.commit()
        self.db.refresh(job)
        return job