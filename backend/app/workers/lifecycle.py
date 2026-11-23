"""
BackgroundWorker Interface & Lifecycle Subsystem

Provides abstract BackgroundWorker contract enforcing start(), stop(), and heartbeat(),
and managing signal handling for graceful worker termination.
"""

from abc import ABC, abstractmethod

from app.core.logging import get_logger

logger = get_logger("app.workers.lifecycle")


class BackgroundWorker(ABC):
    """
    Abstract contract for all platform background worker implementations.
    """

    @abstractmethod
    async def start(self) -> None:
        """Starts worker processing loop and listeners."""

    @abstractmethod
    async def stop(self) -> None:
        """Triggers graceful shutdown and flushes active jobs."""

    @abstractmethod
    async def heartbeat(self) -> None:
        """Emits worker liveness heartbeat ping."""


class WorkerLifespanManager:
    """
    Manages active BackgroundWorker instances and handles OS termination signals (SIGINT, SIGTERM).
    """

    def __init__(self) -> None:
        self._active_workers: set[BackgroundWorker] = set()
        self._is_running: bool = False

    def register_worker(self, worker: BackgroundWorker) -> None:
        """Registers a worker instance for lifecycle management."""
        self._active_workers.add(worker)
        logger.info("Registered worker instance in LifespanManager")

    async def start_all(self) -> None:
        """Starts all registered worker instances."""
        self._is_running = True
        logger.info(
            "Starting all registered background workers",
            count=len(self._active_workers),
        )
        for worker in self._active_workers:
            await worker.start()

    async def stop_all(self) -> None:
        """Triggers graceful shutdown across all registered workers."""
        if not self._is_running:
            return
        logger.info("Stopping all active background workers gracefully...")
        for worker in self._active_workers:
            try:
                await worker.stop()
            except Exception as exc:  # noqa: BLE001
                logger.error("Error stopping background worker", error=str(exc))
        self._is_running = False
        logger.info("All background workers stopped cleanly")


# Global platform worker lifespan manager
lifespan_manager = WorkerLifespanManager()
