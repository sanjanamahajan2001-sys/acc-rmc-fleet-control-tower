"""
Exponential Backoff Retry Engine

Provides retry delay calculation and execution handling for failed worker jobs.
"""

import asyncio

from app.core.logging import get_logger
from app.workers.dlq import dlq_instance
from app.workers.job import JobExecutionContext, JobStatus

logger = get_logger("app.workers.retry")


class RetryPolicy:
    """
    Calculates exponential backoff delay and handles job retries.
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay_sec: float = 1.0,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay_sec = initial_delay_sec

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculates delay in seconds: initial_delay * (backoff_factor ^ (attempt - 1))
        """
        if attempt <= 0:
            return 0.0
        return self.initial_delay_sec * (self.backoff_factor ** (attempt - 1))

    async def handle_failure(
        self, job_ctx: JobExecutionContext, error: Exception
    ) -> bool:
        """
        Handles job execution failure. If attempts < max_retries, sets status to RETRYING
        and returns True. If max_retries reached, routes job to DLQ and returns False.
        """
        job_ctx.metadata.attempts += 1
        job_ctx.metadata.error_message = str(error)

        if job_ctx.metadata.attempts <= job_ctx.metadata.max_retries:
            job_ctx.metadata.status = JobStatus.RETRYING
            delay = self.calculate_delay(job_ctx.metadata.attempts)
            logger.info(
                "Job execution failed, scheduling retry",
                job_id=job_ctx.metadata.job_id,
                attempt=job_ctx.metadata.attempts,
                max_retries=job_ctx.metadata.max_retries,
                delay_sec=delay,
            )
            await asyncio.sleep(delay)
            return True

        # Max retries exhausted -> Route to DLQ
        await dlq_instance.push_to_dlq(
            job_ctx,
            reason=f"Max retries ({job_ctx.metadata.max_retries}) exhausted: {error!s}",
        )
        return False
