from typer.testing import CliRunner
import pytest
from app.cli.app import app as root_app
from app.models.job import JobState


runner = CliRunner()


class SessionWrapper:
    """Wrapper around test DB session to prevent CLI commands from closing the transaction before rollback."""
    def __init__(self, session):
        self._session = session

    def __getattr__(self, item):
        if item == "close":
            return lambda: None
        return getattr(self._session, item)


@pytest.fixture(autouse=True)
def patch_db_session(monkeypatch, db):
    wrapper = SessionWrapper(db)
    monkeypatch.setattr("app.cli.main.SessionLocal", lambda: wrapper)
    monkeypatch.setattr("app.cli.dlq.SessionLocal", lambda: wrapper)
    monkeypatch.setattr("app.db.database.SessionLocal", lambda: wrapper)


def test_cli_enqueue_basic(repository):
    result = runner.invoke(root_app, ["enqueue", "echo CLIBasic"])
    assert result.exit_code == 0
    assert "Job created:" in result.stdout

    jobs = repository.list_all()
    assert any(j.command == "echo CLIBasic" for j in jobs)


def test_cli_enqueue_with_options(repository):
    result = runner.invoke(root_app, [
        "enqueue", "echo CLIOpts",
        "--priority", "10",
        "--timeout", "5",
        "--run-at", "2026-07-17T20:00:00"
    ])
    assert result.exit_code == 0
    assert "priority: 10" in result.stdout
    assert "timeout: 5s" in result.stdout
    assert "scheduled: 2026-07-17 20:00:00" in result.stdout


def test_cli_enqueue_invalid_run_at():
    result = runner.invoke(root_app, ["enqueue", "echo BadDate", "--run-at", "invalid-date"])
    assert result.exit_code == 0
    assert "Invalid datetime format" in result.stdout


def test_cli_status(sample_job):
    result = runner.invoke(root_app, ["status"])
    assert result.exit_code == 0
    assert "=== Queue Status ===" in result.stdout
    assert "=== Job Summary ===" in result.stdout
    assert "=== Metrics ===" in result.stdout


def test_cli_list(sample_job, failed_job):
    result = runner.invoke(root_app, ["list"])
    assert result.exit_code == 0
    assert sample_job.id in result.stdout
    assert failed_job.id in result.stdout

    # Filter by state
    res_dead = runner.invoke(root_app, ["list", "--state", "dead"])
    assert res_dead.exit_code == 0
    assert failed_job.id in res_dead.stdout
    assert sample_job.id not in res_dead.stdout

    # Invalid state
    res_invalid = runner.invoke(root_app, ["list", "--state", "bogus"])
    assert "Invalid state: bogus" in res_invalid.stdout


def test_cli_logs(sample_job):
    # Job with no logs
    result = runner.invoke(root_app, ["logs", sample_job.id])
    assert result.exit_code == 0
    assert "No output recorded" in result.stdout

    # Missing job
    res_missing = runner.invoke(root_app, ["logs", "non-existent-id"])
    assert "Job not found" in res_missing.stdout


def test_cli_dead(repository, sample_job):
    result = runner.invoke(root_app, ["dead", sample_job.id])
    assert result.exit_code == 0
    assert "manually marked as DEAD" in result.stdout

    updated = repository.get_by_id(sample_job.id)
    assert updated.state == JobState.DEAD


def test_cli_config(monkeypatch):
    # Test setting config and listing config
    res_set = runner.invoke(root_app, ["config", "set", "max-retries", "5"])
    assert res_set.exit_code == 0
    assert "Set max-retries = 5" in res_set.stdout

    res_list = runner.invoke(root_app, ["config", "list"])
    assert res_list.exit_code == 0
    assert "max-retries = 5" in res_list.stdout

    # Reset back to default
    runner.invoke(root_app, ["config", "set", "max-retries", "3"])


def test_cli_dlq_list_and_retry(repository, failed_job):
    res_list = runner.invoke(root_app, ["dlq", "list"])
    assert res_list.exit_code == 0
    assert failed_job.id in res_list.stdout

    res_retry = runner.invoke(root_app, ["dlq", "retry", failed_job.id])
    assert res_retry.exit_code == 0
    assert f"Job {failed_job.id} moved back to queue" in res_retry.stdout

    updated = repository.get_by_id(failed_job.id)
    assert updated.state == JobState.PENDING

