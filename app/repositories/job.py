from __future__ import annotations

from datetime import datetime
from sqlalchemy import func, select

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

    def get_by_id_for_update(self, job_id: str) -> Job | None:
        stmt = select(Job).where(Job.id == job_id).with_for_update()
        return self.db.scalar(stmt)

    def list_all(self) -> list[Job]:
        stmt = select(Job)
        return list(self.db.scalars(stmt))

    def list(self) -> list[Job]:
        return self.list_all()

    def list_by_state(self, state: JobState) -> list[Job]:
        stmt = select(Job).where(Job.state == state)
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

    def get_scheduled_jobs(self) -> list[Job]:
        """Get pending jobs whose run_at time has arrived."""
        stmt = (
            select(Job)
            .where(Job.state == JobState.PENDING)
            .where(Job.run_at.is_not(None))
            .where(Job.run_at <= datetime.utcnow())
            .where(Job.next_retry_at.is_(None))
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

    def count_by_state(self) -> dict[str, int]:
        """Return count of jobs grouped by state."""
        stmt = (
            select(Job.state, func.count(Job.id))
            .group_by(Job.state)
        )
        results = self.db.execute(stmt).all()
        counts = {s.value: 0 for s in JobState}
        for state, count in results:
            counts[state.value] = count
        return counts

    def get_stats(self) -> dict:
        """Return execution statistics."""
        counts = self.count_by_state()
        total = sum(counts.values())

        # Average duration for completed jobs
        avg_duration_stmt = (
            select(func.avg(Job.duration_ms))
            .where(Job.duration_ms.is_not(None))
        )
        avg_duration = self.db.scalar(avg_duration_stmt)

        completed = counts.get("completed", 0)
        failed = counts.get("failed", 0) + counts.get("dead", 0)
        timed_out = counts.get("timed_out", 0)
        success_rate = (completed / (completed + failed + timed_out) * 100) if (completed + failed + timed_out) > 0 else 0

        return {
            "total_jobs": total,
            "counts": counts,
            "avg_duration_ms": round(avg_duration, 2) if avg_duration else None,
            "success_rate": round(success_rate, 1),
            "timed_out": timed_out,
        }
