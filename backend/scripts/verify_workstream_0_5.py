"""
Manual Operational Verification Script for Workstream 0.5
"""
import asyncio
from fastapi.testclient import TestClient
from app.factory import create_app
from app.core.redis import check_redis_health
from app.events.bus import InMemoryEventBus
from app.events.schema import BaseEvent, SystemEventNames
from app.workers import (
    task_queue,
    JobStatus,
    RetryPolicy,
    dlq_instance,
    heartbeat_monitor,
    scheduler_instance,
)

app = create_app()
client = TestClient(app)


async def main_async():
    print("=== Workstream 0.5 Manual Operational Verification Starting ===")

    # 1. Async Redis Health Check Verification
    redis_health = await check_redis_health()
    print(f"✓ Redis Async Health Check: {redis_health}")
    assert redis_health["status"] == "healthy"

    # 2. EventBus Pub/Sub Verification
    bus = InMemoryEventBus()
    received = []

    async def mock_handler(event: BaseEvent[dict]):
        received.append(event)

    bus.subscribe(SystemEventNames.WORKER_STARTED, mock_handler)
    test_event = BaseEvent[dict](
        event_type=SystemEventNames.WORKER_STARTED,
        payload={"node_id": "worker-node-1"},
        correlation_id="manual-corr-05",
        request_id="manual-req-05",
    )
    await bus.publish(test_event)
    assert len(received) == 1
    assert received[0].payload == {"node_id": "worker-node-1"}
    print(f"✓ EventBus Pub/Sub Verified: Event '{received[0].event_type}' dispatched successfully")

    # 3. TaskQueue & Execution Verification
    task_runs = []

    async def sample_task(payload: dict):
        task_runs.append(payload["item"])

    task_queue.register_task("sample.task", sample_task)
    job_id = await task_queue.enqueue("sample.task", {"item": "item-100"})
    print(f"✓ Enqueued Task Job ID: {job_id}")

    processed = await task_queue.process_next_job()
    assert processed is True
    assert task_runs == ["item-100"]
    print("✓ TaskQueue Dequeued & Executed Task Successfully")

    # 4. Worker Heartbeat Monitor & Scheduler Start
    await heartbeat_monitor.start()
    await asyncio.sleep(0.05)
    hb_status = heartbeat_monitor.get_status()
    assert hb_status["status"] == "healthy"
    print(f"✓ Worker Heartbeat Monitor Status: {hb_status}")

    # 5. Readiness Endpoint Integration Verification
    res_ready = client.get("/api/v1/health/readiness")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["success"] is True
    components = ready_data["data"]["components"]
    assert components["redis"]["status"] == "healthy"
    assert components["worker_heartbeat"]["status"] == "healthy"
    assert "queue_depth" in components["worker_metrics"]
    print("✓ GET /api/v1/health/readiness Verified with Live Redis & Worker Metrics:")
    print(f"  Redis: {components['redis']}")
    print(f"  Worker Heartbeat: {components['worker_heartbeat']}")
    print(f"  Worker Metrics: {components['worker_metrics']}")

    await heartbeat_monitor.stop()
    print("=== Workstream 0.5 Manual Verification PASSED ===")


if __name__ == "__main__":
    asyncio.run(main_async())
