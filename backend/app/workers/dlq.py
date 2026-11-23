"""
Dead Letter Queue (DLQ) Subsystem

Provides DLQ abstraction storing exhausted failed tasks for manual inspection and replay.
"""

from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.workers.job import JobExecutionContext, JobStatus

logger = get_logger("app.workers.dlq")


class DeadLetterQueue(ABC):
    """
    Abstract Dead Letter Queue interface.
    """

    @abstractmethod
    async def push_to_dlq(self, job_ctx: JobExecutionContext, reason: str) -> None:
        """Pushes an exhausted failed job to DLQ storage."""

    @abstractmethod
    async def get_dlq_jobs(self, limit: int = 50) -> list[JobExecutionContext]:
        """Returns list of jobs currently in DLQ."""


class InMemoryDeadLetterQueue(DeadLetterQueue):
    """
    In-memory implementation of Dead Letter Queue for testing and single-node processing.
    """

    def __init__(self) -> None:
        self._dlq_store: list[JobExecutionContext] = []

    async def push_to_dlq(self, job_ctx: JobExecutionContext, reason: str) -> None:
        job_ctx.metadata.status = JobStatus.DLQ
        job_ctx.metadata.error_message = reason
        self._dlq_store.append(job_ctx)
        logger.warning(
            "Job routed to Dead Letter Queue (DLQ)",
            job_id=job_ctx.metadata.job_id,
            task_name=job_ctx.metadata.task_name,
            reason=reason,
        )

    async def get_dlq_jobs(self, limit: int = 50) -> list[JobExecutionContext]:
        return self._dlq_store[:limit]


# Global platform DLQ instance
dlq_instance: DeadLetterQueue = InMemoryDeadLetterQueue()
