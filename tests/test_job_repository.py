from datetime import datetime, timedelta
from app.models.job import Job, JobState


def test_create_job(repository):
    job = Job(command="echo Test")
    created = repository.create(job)
    assert created.id is not None
    assert created.command == "echo Test"
    assert created.state == JobState.PENDING


def test_get_by_id(repository, sample_job):
    fetched = repository.get_by_id(sample_job.id)
    assert fetched is not None
    assert fetched.id == sample_job.id
    assert fetched.command == sample_job.command


def test_update_job(repository, sample_job):
    sample_job.state = JobState.PROCESSING
    sample_job.attempts = 1
    updated = repository.update(sample_job)
    assert updated.state == JobState.PROCESSING
    assert updated.attempts == 1

    fetched = repository.get_by_id(sample_job.id)
    assert fetched.state == JobState.PROCESSING


def test_delete_job(repository, sample_job):
    job_id = sample_job.id
    repository.delete(sample_job)
    assert repository.get_by_id(job_id) is None


def test_list_all(repository, sample_job):
    jobs = repository.list_all()
    assert any(j.id == sample_job.id for j in jobs)


def test_list_by_state(repository, sample_job, failed_job):
    pending_jobs = repository.list_by_state(JobState.PENDING)
    assert any(j.id == sample_job.id for j in pending_jobs)
    assert not any(j.id == failed_job.id for j in pending_jobs)

    dead_jobs = repository.list_by_state(JobState.DEAD)
    assert any(j.id == failed_job.id for j in dead_jobs)


def test_get_retryable_jobs(repository):
    # Job past retry time
    past_job = Job(command="retry past", state=JobState.PENDING, next_retry_at=datetime.utcnow() - timedelta(seconds=10))
    repository.create(past_job)

    # Job future retry time
    future_job = Job(command="retry future", state=JobState.PENDING, next_retry_at=datetime.utcnow() + timedelta(hours=1))
    repository.create(future_job)

    retryable = repository.get_retryable_jobs()
    retryable_ids = [j.id for j in retryable]
    assert past_job.id in retryable_ids
    assert future_job.id not in retryable_ids


def test_get_scheduled_jobs(repository):
    # Scheduled for past
    ready_job = Job(command="sched ready", state=JobState.PENDING, run_at=datetime.utcnow() - timedelta(seconds=5))
    repository.create(ready_job)

    # Scheduled for future
    future_job = Job(command="sched future", state=JobState.PENDING, run_at=datetime.utcnow() + timedelta(hours=1))
    repository.create(future_job)

    scheduled = repository.get_scheduled_jobs()
    scheduled_ids = [j.id for j in scheduled]
    assert ready_job.id in scheduled_ids
    assert future_job.id not in scheduled_ids


def test_reset_dead_job(repository, failed_job):
    reset = repository.reset_dead_job(failed_job)
    assert reset.state == JobState.PENDING
    assert reset.attempts == 0
    assert reset.next_retry_at is None
    assert reset.last_error is None


def test_get_stats(repository, sample_job, failed_job):
    stats = repository.get_stats()
    assert stats["total_jobs"] >= 2
    assert "counts" in stats
    assert stats["counts"]["pending"] >= 1
    assert stats["counts"]["dead"] >= 1
