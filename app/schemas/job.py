from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class JobState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class JobCreate(BaseModel):
    command: str
    max_retries: int = 3


class JobResponse(BaseModel):
    id: str
    command: str
    state: JobState
    attempts: int
    max_retries: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)