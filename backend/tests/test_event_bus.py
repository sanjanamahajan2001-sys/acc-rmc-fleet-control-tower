"""
Unit tests for EventBus Subsystem
"""

import pytest

from app.events.bus import InMemoryEventBus
from app.events.schema import BaseEvent, SystemEventNames


@pytest.mark.asyncio
async def test_in_memory_event_bus_pub_sub():
    bus = InMemoryEventBus()
    received_events = []

    async def sample_handler(event: BaseEvent[dict]):
        received_events.append(event)

    bus.subscribe(SystemEventNames.WORKER_STARTED, sample_handler)

    test_event = BaseEvent[dict](
        event_type=SystemEventNames.WORKER_STARTED,
        payload={"node": "worker-1"},
        correlation_id="corr-bus-1",
        request_id="req-bus-1",
    )

    await bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].event_id == test_event.event_id
    assert received_events[0].payload == {"node": "worker-1"}

    bus.unsubscribe(SystemEventNames.WORKER_STARTED, sample_handler)
    await bus.publish(test_event)
    assert len(received_events) == 1  # Unsubscribed, no extra event
