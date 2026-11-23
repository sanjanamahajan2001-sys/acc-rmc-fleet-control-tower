"""
Worker Heartbeat Monitor

Publishes periodic system.worker.heartbeat events across event bus
and updates live worker health metrics for readiness probes.
"""

import asyncio
import time
from typing import Any

from app.core.logging import get_logger
from app.events.bus import event_bus
from app.events.schema import BaseEvent, SystemEventNames

logger = get_logger("app.workers.heartbeat")


class WorkerHeartbeatMonitor:
    """
    Periodic heartbeat monitor emitting worker liveness events.
    """

    def __init__(self, interval_seconds: float = 10.0) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._last_heartbeat_time: float = 0.0
        self._is_alive: bool = False

    async def start(self) -> None:
        """Starts periodic heartbeat publishing loop."""
        self._is_alive = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Worker heartbeat monitor started", interval=self.interval_seconds)

    async def stop(self) -> None:
        """Stops heartbeat monitor loop."""
        self._is_alive = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Worker heartbeat monitor stopped cleanly")

    async def _heartbeat_loop(self) -> None:
        while self._is_alive:
            self._last_heartbeat_time = time.time()
            event = BaseEvent[dict](
                event_type=SystemEventNames.WORKER_HEARTBEAT,
                payload={"status": "alive", "timestamp": self._last_heartbeat_time},
                correlation_id="system-heartbeat-corr",
                request_id="system-heartbeat-req",
            )
            await event_bus.publish(event)
            await asyncio.sleep(self.interval_seconds)

    def get_status(self) -> dict[str, Any]:
        """Returns health probe status of worker heartbeat."""
        return {
            "status": "healthy" if self._is_alive else "stopped",
            "last_heartbeat_age_sec": (
                round(time.time() - self._last_heartbeat_time, 2)
                if self._last_heartbeat_time > 0
                else -1
            ),
        }


# Global platform worker heartbeat monitor instance
heartbeat_monitor = WorkerHeartbeatMonitor()
