from app.models.job import Job, JobState


def test_stats_empty_database(repository):
    stats = repository.get_stats()
    assert stats["total_jobs"] == 0
    assert stats["avg_duration_ms"] is None
    assert stats["success_rate"] == 0.0
    assert stats["timed_out"] == 0


def test_stats_calculations_with_jobs(repository):
    # Completed job 1 with 100ms
    j1 = Job(command="cmd1", state=JobState.COMPLETED, duration_ms=100)
    repository.create(j1)

    # Completed job 2 with 300ms -> avg should be 200ms
    j2 = Job(command="cmd2", state=JobState.COMPLETED, duration_ms=300)
    repository.create(j2)

    # Failed job
    j3 = Job(command="cmd3", state=JobState.FAILED)
    repository.create(j3)

    # Dead job
    j4 = Job(command="cmd4", state=JobState.DEAD)
    repository.create(j4)

    # Timed out job
    j5 = Job(command="cmd5", state=JobState.TIMED_OUT)
    repository.create(j5)

    stats = repository.get_stats()
    assert stats["total_jobs"] == 5
    assert stats["avg_duration_ms"] == 200.0
    # Success rate: completed (2) / (completed (2) + failed (1) + dead (1) + timed_out (1)) = 2/5 = 40.0%
    assert stats["success_rate"] == 40.0
    assert stats["timed_out"] == 1
    assert stats["counts"]["completed"] == 2
    assert stats["counts"]["failed"] == 1
    assert stats["counts"]["dead"] == 1
