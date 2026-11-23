"""
Unit tests for TaskQueue, Retry Policy & DLQ Routing
"""

import pytest

from app.workers.dlq import dlq_instance
from app.workers.job import JobExecutionContext, JobMetadata
from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy


@pytest.mark.asyncio
async def test_task_queue_enqueue_and_process():
    queue = TaskQueue()
    results = []

    async def mock_handler(payload: dict):
        results.append(payload["msg"])

    queue.register_task("test.task", mock_handler)
    job_id = await queue.enqueue("test.task", {"msg": "hello"})
    assert len(job_id) > 0

    processed = await queue.process_next_job()
    assert processed is True
    assert results == ["hello"]

    metrics = queue.get_metrics()
    assert metrics.completed_jobs == 1
    assert metrics.failed_jobs == 0


@pytest.mark.asyncio
async def test_task_retry_and_dlq_routing():
    fast_retry = RetryPolicy(max_retries=1, backoff_factor=1.0, initial_delay_sec=0.01)
    queue = TaskQueue(retry_policy=fast_retry)

    attempts = 0

    async def failing_handler(payload: dict):
        nonlocal attempts
        attempts += 1
        raise ValueError("Simulated task failure")

    queue.register_task("failing.task", failing_handler)

    # Manually enqueue job with max_retries=1 override in metadata
    meta = JobMetadata(
        task_name="failing.task",
        max_retries=1,
        correlation_id="corr-1",
        request_id="req-1",
    )
    job_ctx = JobExecutionContext(metadata=meta, payload={})
    await queue._queue.put(job_ctx)

    # Attempt 1: Fails -> RETRYING -> Re-enqueued
    await queue.process_next_job()
    assert attempts == 1

    # Attempt 2: Fails -> Max retries (1) reached -> Routed to DLQ
    await queue.process_next_job()
    assert attempts == 2

    dlq_jobs = await dlq_instance.get_dlq_jobs()
    assert len(dlq_jobs) >= 1
    assert dlq_jobs[-1].metadata.task_name == "failing.task"
