"""
Unit tests for Event Envelope Schema & System Event Names
"""

from app.events.schema import BaseEvent, SystemEventNames


def test_event_schema_creation():
    event = BaseEvent[dict](
        event_type=SystemEventNames.WORKER_STARTED,
        payload={"worker_id": "W1"},
        correlation_id="corr-event-1",
        request_id="req-event-1",
    )

    assert event.event_id is not None
    assert event.event_type == "system.worker.started"
    assert event.payload == {"worker_id": "W1"}
    assert event.correlation_id == "corr-event-1"
    assert event.request_id == "req-event-1"
