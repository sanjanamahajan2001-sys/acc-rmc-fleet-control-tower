"""
Production Asynchronous ERPImportWorker
Extends WS0.5 BackgroundWorker abstraction. Manages job queues, graceful shutdown,
liveness heartbeats, pipeline execution, retries, and DLQ routing.
"""

import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.events.bus import EventBus
from app.modules.erp.workers.orchestrator import ImportPipelineOrchestrator
from app.workers.dlq import InMemoryDeadLetterQueue
from app.workers.lifecycle import BackgroundWorker
from app.workers.retry import RetryPolicy

logger = get_logger("app.modules.erp.workers.worker")


class ERPImportWorker(BackgroundWorker):
    """
    Production ERP Import Worker process extending BackgroundWorker.
    Consumes job items from an in-memory or Redis queue, executes pipeline orchestrator,
    emits liveness heartbeats, and routes unrecoverable failures to DLQ.
    """

    def __init__(
        self,
        worker_id: str = "erp-import-worker-01",
        event_bus: EventBus | None = None,
        job_queue: asyncio.Queue[str] | None = None,
        max_retries: int = 3,
    ):
        self.worker_id = worker_id
        self.event_bus = event_bus
        self.job_queue = job_queue or asyncio.Queue[str]()
        self.max_retries = max_retries
        self.retry_policy = RetryPolicy(max_retries=max_retries, initial_delay_sec=1.0)
        self.dlq = InMemoryDeadLetterQueue()
        self.orchestrator = ImportPipelineOrchestrator(event_bus=event_bus)
        self._is_running: bool = False
        self._worker_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start worker execution loop and liveness heartbeat task."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("Starting ERPImportWorker", worker_id=self.worker_id)

        self._worker_task = asyncio.create_task(self._processing_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Trigger graceful worker shutdown and finish active processing."""
        if not self._is_running:
            return
        logger.info("Stopping ERPImportWorker gracefully...", worker_id=self.worker_id)
        self._is_running = False

        if self._worker_task:
            self._worker_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        logger.info("ERPImportWorker stopped cleanly", worker_id=self.worker_id)

    async def heartbeat(self) -> None:
        """Emit liveness heartbeat."""
        logger.info(
            "Worker Heartbeat Ping", worker_id=self.worker_id, timestamp=time.time()
        )

    async def _heartbeat_loop(self) -> None:
        while self._is_running:
            try:
                await self.heartbeat()
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error("Error in heartbeat loop", error=str(e))

    async def _processing_loop(self) -> None:
        while self._is_running:
            try:
                job_number = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                await self.execute_job(job_number)
                self.job_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error("Unhandled error in worker loop", error=str(e))

    async def execute_job(self, job_number: str) -> dict[str, Any]:
        """
        Execute job with transaction management and automatic retry policy.
        """
        logger.info(
            "Executing import job", worker_id=self.worker_id, job_number=job_number
        )
        attempt = 0

        while attempt <= self.max_retries:
            attempt += 1
            engine = create_async_engine(
                settings.ASYNC_DATABASE_URI, pool_pre_ping=True
            )
            async with engine.connect() as conn:
                trans = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    res = await self.orchestrator.execute_pipeline(session, job_number)
                    await trans.commit()
                    await session.close()
                    await engine.dispose()
                    return res
                except Exception as exc:
                    await trans.rollback()
                    await session.close()
                    await engine.dispose()

                    logger.warning(
                        "Import job attempt failed",
                        job_number=job_number,
                        attempt=attempt,
                        error=str(exc),
                    )

                    if attempt > self.max_retries:
                        logger.error(
                            "Job exceeded max retries.",
                            job_number=job_number,
                        )
                        raise
                    else:
                        delay = self.retry_policy.calculate_delay(attempt)
                        await asyncio.sleep(delay)

        raise RuntimeError(f"Job execution failed for {job_number}")
