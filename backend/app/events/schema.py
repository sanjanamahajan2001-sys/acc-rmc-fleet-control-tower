"""
Standardized Internal Event Envelope Schema

Defines BaseEvent[T] and dot-notation system event naming standards
(<domain>.<entity>.<action>).
"""

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SystemEventNames:
    """
    Standardized dot-notation event names for platform system operations.
    """

    WORKER_STARTED = "system.worker.started"
    WORKER_STOPPED = "system.worker.stopped"
    WORKER_HEARTBEAT = "system.worker.heartbeat"
    QUEUE_ENQUEUED = "system.queue.enqueued"
    QUEUE_FAILED = "system.queue.failed"
    QUEUE_RETRY = "system.queue.retry"
    QUEUE_DLQ = "system.queue.dlq"


class BaseEvent(BaseModel, Generic[T]):
    """
    Standardized internal event schema published across the event bus.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique event UUID"
    )
    event_type: str = Field(
        description="Dot-notation event name (e.g. system.worker.started)"
    )
    payload: T = Field(description="Typed event payload data")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of event creation",
    )
    correlation_id: str = Field(description="Distributed trace correlation ID")
    request_id: str = Field(description="Origin request ID")
