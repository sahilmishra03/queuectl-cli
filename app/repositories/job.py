from sqlalchemy import select

from app.models.job import Job
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

    def delete(self, job: Job) -> None:
        self.db.delete(job)
        self.db.commit()