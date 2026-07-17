from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class JobState(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"
    TIMED_OUT = "timed_out"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    command: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    state: Mapped[JobState] = mapped_column(
        SqlEnum(
            JobState,
            values_callable=lambda enum: [e.value for e in enum],
            name="jobstate",
        ),
        default=JobState.PENDING,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
    )

    timeout: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    stdout: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    stderr: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )