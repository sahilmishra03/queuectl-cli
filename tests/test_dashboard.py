from fastapi.testclient import TestClient
import pytest
from app.dashboard.dashboard import dashboard_app
from app.models.job import JobState

client = TestClient(dashboard_app)


class SessionWrapper:
    def __init__(self, session):
        self._session = session

    def __getattr__(self, item):
        if item == "close":
            return lambda: None
        return getattr(self._session, item)


@pytest.fixture(autouse=True)
def patch_dashboard_db(monkeypatch, db):
    monkeypatch.setattr("app.dashboard.dashboard.SessionLocal", lambda: SessionWrapper(db))


def test_dashboard_html_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "QueueCTL Dashboard" in response.text


def test_api_stats(sample_job, failed_job):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "counts" in data
    assert "queue_size" in data


def test_api_jobs(sample_job, failed_job):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(j["id"] == sample_job.id for j in data)

    # Filter by state
    res_pending = client.get("/api/jobs?state=pending")
    assert res_pending.status_code == 200
    data_pending = res_pending.json()
    assert any(j["id"] == sample_job.id for j in data_pending)
    assert not any(j["id"] == failed_job.id for j in data_pending)

    # Filter by invalid state fallback to all
    res_bogus = client.get("/api/jobs?state=invalid_state_name")
    assert res_bogus.status_code == 200
    assert len(res_bogus.json()) == len(data)


def test_api_job_detail(sample_job):
    response = client.get(f"/api/jobs/{sample_job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_job.id
    assert data["command"] == sample_job.command
    assert data["state"] == JobState.PENDING.value

    # Missing job
    res_missing = client.get("/api/jobs/non-existent-id")
    assert res_missing.status_code == 200
    assert "error" in res_missing.json()
