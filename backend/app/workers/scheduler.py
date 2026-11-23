"""
Cron Scheduler Foundation Subsystem

Provides async Cron scheduler loop executing registered periodic tasks on schedule.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from app.core.logging import get_logger

logger = get_logger("app.workers.scheduler")

ScheduledTask = Callable[[], Awaitable[None]]


class Scheduler:
    """
    Async Cron Scheduler foundation executing periodic tasks.
    """

    def __init__(self) -> None:
        self._tasks: list[tuple[str, float, ScheduledTask]] = []
        self._is_running: bool = False
        self._loop_task: asyncio.Task | None = None

    def schedule_periodic_task(
        self, name: str, interval_seconds: float, task: ScheduledTask
    ) -> None:
        """Schedules a periodic task to run every interval_seconds."""
        self._tasks.append((name, interval_seconds, task))
        logger.info("Scheduled periodic task", name=name, interval=interval_seconds)

    async def start(self) -> None:
        """Starts background scheduler loop."""
        self._is_running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler engine started", scheduled_task_count=len(self._tasks))

    async def stop(self) -> None:
        """Stops background scheduler loop cleanly."""
        self._is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler engine stopped cleanly")

    async def _scheduler_loop(self) -> None:
        # Initialize last run timestamp to 0.0 to trigger immediate first execution if due
        last_run_map: dict[str, float] = {name: 0.0 for name, _, _ in self._tasks}
        while self._is_running:
            now = time.time()
            for name, interval, task in self._tasks:
                if now - last_run_map.get(name, 0.0) >= interval:
                    last_run_map[name] = now
                    try:
                        logger.info("Executing scheduled task", name=name)
                        await task()
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Error executing scheduled task", name=name, error=str(exc)
                        )
            await asyncio.sleep(0.01)


# Global platform scheduler instance
scheduler_instance = Scheduler()
