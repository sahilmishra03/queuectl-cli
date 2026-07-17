import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.job import Job, JobState
from app.repositories.job import JobRepository
from app.services.queue import QueueService
from app.core.config import settings


# Use an in-memory SQLite database for isolated, fast testing without touching real Postgres
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db():
    """Provide a DB session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()



@pytest.fixture
def repository(db):
    """Provide a JobRepository backed by the test session."""
    return JobRepository(db)


from app.db.redis import redis_client


@pytest.fixture(autouse=True)
def clean_redis():
    """Clear Redis queue before and after every test."""
    redis_client.delete(QueueService.QUEUE_KEY)
    yield
    redis_client.delete(QueueService.QUEUE_KEY)


@pytest.fixture
def queue():
    """Provide a QueueService."""
    return QueueService()



@pytest.fixture
def sample_job(db, repository):
    """Create and return a sample job."""
    job = Job(command="echo Hello", max_retries=3)
    repository.create(job)
    return job


@pytest.fixture
def failed_job(db, repository):
    """Create a job in DEAD state."""
    job = Job(command="badcmd", max_retries=3)
    job.state = JobState.DEAD
    job.attempts = 3
    job.last_error = "command not found"
    repository.create(job)
    return job
