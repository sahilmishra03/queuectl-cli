import sys
from datetime import datetime, timedelta
import pytest
from app.models.job import Job, JobState
from app.services.worker import WorkerService


def test_process_completed_job(repository, queue):
    job = Job(command="echo WorkerSuccess")
    repository.create(job)
    queue.enqueue(job.id)

    worker = WorkerService(repository, queue)
    worker._process(job.id)

    updated = repository.get_by_id(job.id)
    assert updated.state == JobState.COMPLETED
    assert updated.started_at is not None
    assert updated.completed_at is not None
    assert updated.duration_ms is not None
    assert "WorkerSuccess" in updated.stdout


def test_process_failed_job_and_retry_scheduling(repository, queue):
    job = Job(command="badcmd_xyz_123", max_retries=3)
    repository.create(job)
    queue.enqueue(job.id)

    worker = WorkerService(repository, queue)
    worker._process(job.id)

    updated = repository.get_by_id(job.id)
    assert updated.state == JobState.PENDING
    assert updated.attempts == 1
    assert updated.next_retry_at is not None
    assert updated.last_error is not None


def test_process_dead_state(repository, queue):
    job = Job(command="badcmd_xyz_123", max_retries=1)
    repository.create(job)
    queue.enqueue(job.id)

    worker = WorkerService(repository, queue)
    worker._process(job.id)

    updated = repository.get_by_id(job.id)
    assert updated.state == JobState.DEAD
    assert updated.attempts == 1
    assert updated.next_retry_at is None


def test_process_timeout_state(repository, queue):
    python_exe = sys.executable
    cmd = f'"{python_exe}" -c "import time; time.sleep(3)"'
    job = Job(command=cmd, timeout=1)
    repository.create(job)
    queue.enqueue(job.id)

    worker = WorkerService(repository, queue)
    worker._process(job.id)

    updated = repository.get_by_id(job.id)
    assert updated.state == JobState.TIMED_OUT
    assert "timed out after 1 seconds" in updated.last_error


def test_process_output_logging(repository, queue):
    python_exe = sys.executable
    cmd = f'"{python_exe}" -c "import sys; print(\'out_log\'); print(\'err_log\', file=sys.stderr)"'
    job = Job(command=cmd)
    repository.create(job)
    queue.enqueue(job.id)

    worker = WorkerService(repository, queue)
    worker._process(job.id)

    updated = repository.get_by_id(job.id)
    assert updated.state == JobState.COMPLETED
    assert "out_log" in updated.stdout
    assert "err_log" in updated.stderr


def test_worker_start_polling(repository, queue, monkeypatch):
    # Create a scheduled job whose run_at has arrived
    sched_job = Job(command="echo Sched", state=JobState.PENDING, run_at=datetime.utcnow() - timedelta(seconds=5))
    repository.create(sched_job)

    # Create a retryable job whose retry time has arrived
    retry_job = Job(command="echo Retry", state=JobState.PENDING, next_retry_at=datetime.utcnow() - timedelta(seconds=5), attempts=1)
    repository.create(retry_job)

    worker = WorkerService(repository, queue)

    # Monkeypatch time.sleep to break the while True loop after 1 cycle
    def mock_sleep(seconds):
        raise StopIteration("Break loop")

    monkeypatch.setattr("time.sleep", mock_sleep)

    with pytest.raises(StopIteration):
        worker.start()

    # Both jobs should now be enqueued in Redis and their scheduling fields reset
    assert queue.size() == 2
    updated_sched = repository.get_by_id(sched_job.id)
    assert updated_sched.run_at is None

    updated_retry = repository.get_by_id(retry_job.id)
    assert updated_retry.next_retry_at is None


def test_priority_execution(repository, queue):
    job_low = Job(command="echo Low", priority=1)
    job_high = Job(command="echo High", priority=10)
    repository.create(job_low)
    repository.create(job_high)

    queue.enqueue(job_low.id, priority=job_low.priority)
    queue.enqueue(job_high.id, priority=job_high.priority)

    worker = WorkerService(repository, queue)

    # First dequeued job should be job_high
    first_id = queue.dequeue()
    assert first_id == job_high.id
    worker._process(first_id)
    assert repository.get_by_id(job_high.id).state == JobState.COMPLETED

    # Second dequeued job should be job_low
    second_id = queue.dequeue()
    assert second_id == job_low.id
    worker._process(second_id)
    assert repository.get_by_id(job_low.id).state == JobState.COMPLETED
