"""
Unit tests for Worker Lifecycle, Heartbeat, and Scheduler
"""

import asyncio

import pytest

from app.workers import (
    BackgroundWorker,
    heartbeat_monitor,
    lifespan_manager,
    scheduler_instance,
)


class DummyWorker(BackgroundWorker):
    def __init__(self):
        self.started = False
        self.stopped = False
        self.hb_count = 0

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def heartbeat(self):
        self.hb_count += 1


@pytest.mark.asyncio
async def test_worker_lifespan_manager():
    worker = DummyWorker()
    lifespan_manager.register_worker(worker)

    await lifespan_manager.start_all()
    assert worker.started is True

    await lifespan_manager.stop_all()
    assert worker.stopped is True


@pytest.mark.asyncio
async def test_worker_heartbeat_monitor():
    await heartbeat_monitor.start()
    await asyncio.sleep(0.05)
    status = heartbeat_monitor.get_status()
    assert status["status"] == "healthy"
    await heartbeat_monitor.stop()


@pytest.mark.asyncio
async def test_scheduler_periodic_execution():
    executed = False

    async def scheduled_task():
        nonlocal executed
        executed = True

    scheduler_instance.schedule_periodic_task("test.cron", 0.05, scheduled_task)
    await scheduler_instance.start()
    await asyncio.sleep(0.1)
    await scheduler_instance.stop()

    assert executed is True
