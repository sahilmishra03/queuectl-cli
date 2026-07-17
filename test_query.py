import sys
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.repositories.job import JobRepository
from app.models.job import Job, JobState

db = SessionLocal()
repo = JobRepository(db)

# Create a job with future next_retry_at
job = Job(command="test")
job.state = JobState.PENDING
job.next_retry_at = datetime.utcnow() + timedelta(seconds=10)
repo.create(job)

print(f"Current UTC: {datetime.utcnow()}")
print(f"Job next retry at: {job.next_retry_at}")

jobs = repo.get_retryable_jobs()
print(f"Found {len(jobs)} retryable jobs")
for j in jobs:
    print(f" - Job {j.id}, state={j.state}, next_retry_at={j.next_retry_at}")
