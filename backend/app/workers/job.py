"""
Job Status & Execution Context DTOs

Defines JobStatus enum state machine, JobMetadata, and JobExecutionContext models.
"""

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """
    Standardized worker job lifecycle states.
    """

    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DLQ = "DLQ"


class JobMetadata(BaseModel):
    """
    Metadata container attached to background worker tasks.
    """

    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique job UUID"
    )
    task_name: str = Field(description="Registered task handler name")
    status: JobStatus = Field(
        default=JobStatus.QUEUED, description="Current job lifecycle status"
    )
    attempts: int = Field(
        default=0, ge=0, description="Current execution attempt counter"
    )
    max_retries: int = Field(
        default=3, ge=0, description="Maximum retry limit before DLQ routing"
    )
    correlation_id: str = Field(description="Distributed trace correlation ID")
    request_id: str = Field(description="Origin request ID")
    created_at: float = Field(
        default_factory=time.time, description="Creation epoch timestamp"
    )
    started_at: float | None = Field(
        default=None, description="Execution start epoch timestamp"
    )
    completed_at: float | None = Field(
        default=None, description="Completion epoch timestamp"
    )
    error_message: str | None = Field(
        default=None, description="Error details on failure"
    )


class JobExecutionContext(BaseModel):
    """
    Wrapper coupling JobMetadata with task payload arguments.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: JobMetadata
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Task payload dictionary"
    )
