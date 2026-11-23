"""
Task Queue & Job Execution Engine

Provides TaskQueue abstraction, worker task registration, enqueueing,
task processing loop, and metrics calculation.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.context import RequestContext
from app.core.logging import get_logger
from app.workers.job import JobExecutionContext, JobMetadata, JobStatus
from app.workers.metrics import WorkerMetrics
from app.workers.retry import RetryPolicy

logger = get_logger("app.workers.queue")

TaskHandler = Callable[[dict[str, Any]], Awaitable[None]]


class TaskQueue:
    """
    Async Task Queue engine managing task registration, enqueueing, and execution.
    """

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._queue: asyncio.Queue[JobExecutionContext] = asyncio.Queue()
        self._handlers: dict[str, TaskHandler] = {}
        self._retry_policy = retry_policy or RetryPolicy()

        # Operational Metrics Counters
        self._completed_jobs = 0
        self._failed_jobs = 0
        self._retry_count = 0
        self._total_execution_time_ms = 0.0

    def register_task(self, task_name: str, handler: TaskHandler) -> None:
        """Registers an async handler for a named task."""
        self._handlers[task_name] = handler
        logger.info("Registered background task handler", task_name=task_name)

    async def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        """
        Enqueues a task payload and returns the unique job_id UUID.
        """
        if task_name not in self._handlers:
            raise ValueError(f"Task name '{task_name}' is not registered in TaskQueue")

        meta = JobMetadata(
            task_name=task_name,
            status=JobStatus.QUEUED,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
        )
        job_ctx = JobExecutionContext(metadata=meta, payload=payload)
        await self._queue.put(job_ctx)

        logger.info("Enqueued task", job_id=meta.job_id, task_name=task_name)
        return meta.job_id

    async def process_next_job(self) -> bool:
        """
        Dequeues and executes the next job in queue. Returns True if job executed.
        """
        try:
            job_ctx = await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return False

        task_name = job_ctx.metadata.task_name
        handler = self._handlers[task_name]

        job_ctx.metadata.status = JobStatus.RUNNING
        job_ctx.metadata.started_at = time.time()
        start_time = time.perf_counter()

        # Seed RequestContext for worker execution
        RequestContext.init(
            request_id=job_ctx.metadata.request_id,
            correlation_id=job_ctx.metadata.correlation_id,
        )

        try:
            await handler(job_ctx.payload)
            job_ctx.metadata.status = JobStatus.COMPLETED
            job_ctx.metadata.completed_at = time.time()
            execution_duration_ms = (time.perf_counter() - start_time) * 1000

            self._completed_jobs += 1
            self._total_execution_time_ms += execution_duration_ms
            logger.info(
                "Successfully executed job",
                job_id=job_ctx.metadata.job_id,
                duration_ms=execution_duration_ms,
            )
        except Exception as exc:  # noqa: BLE001
            self._failed_jobs += 1
            logger.error(
                "Job execution failed", job_id=job_ctx.metadata.job_id, error=str(exc)
            )

            should_retry = await self._retry_policy.handle_failure(job_ctx, exc)
            if should_retry:
                self._retry_count += 1
                await self._queue.put(job_ctx)

        self._queue.task_done()
        return True

    def get_metrics(self) -> WorkerMetrics:
        """Returns current operational metrics snapshot."""
        total_finished = self._completed_jobs + self._failed_jobs
        avg_time = (
            round(self._total_execution_time_ms / total_finished, 2)
            if total_finished > 0
            else 0.0
        )
        return WorkerMetrics(
            queue_depth=self._queue.qsize(),
            active_workers=1,
            completed_jobs=self._completed_jobs,
            failed_jobs=self._failed_jobs,
            retry_count=self._retry_count,
            avg_execution_time_ms=avg_time,
        )


# Global platform task queue instance
task_queue = TaskQueue()
