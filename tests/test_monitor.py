import pytest
from app.cli.monitor import get_system_metrics, build_dashboard_layout, run_monitor
from app.repositories.job import JobRepository
from app.services.queue import QueueService


def test_get_system_metrics():
    metrics = get_system_metrics()
    assert "mem_total_gb" in metrics
    assert "mem_used_gb" in metrics
    assert "mem_percent" in metrics
    assert "worker_count" in metrics
    assert "worker_mem_mb" in metrics
    assert isinstance(metrics["worker_count"], int)
    assert isinstance(metrics["mem_percent"], (int, float))


def test_build_dashboard_layout(db, clean_redis, sample_job):
    repository = JobRepository(db)
    queue = QueueService()
    group = build_dashboard_layout(repository, queue)
    assert group is not None
    assert len(group.renderables) == 5  # header, system, stats, table, footer


def test_run_monitor_iterations(monkeypatch, db, clean_redis, sample_job):
    # Patch SessionLocal to use test db session wrapper
    class SessionWrapper:
        def __init__(self, session):
            self._session = session
        def __getattr__(self, item):
            if item in ("close", "expire_all"):
                return lambda: None
            return getattr(self._session, item)

    wrapper = SessionWrapper(db)
    monkeypatch.setattr("app.cli.monitor.SessionLocal", lambda: wrapper)

    # Run monitor for 1 iteration
    run_monitor(refresh_interval=0.1, iterations=1)
