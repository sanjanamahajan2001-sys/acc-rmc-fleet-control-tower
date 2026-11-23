"""
Workstream 2.11 Synchronization Connection & Event Manager
In-memory event bus & SSE client registry for real-time push notifications.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator
from app.modules.site_dashboard.sync.dtos import SyncEventDTO


class SyncManager:
    """Manages active SSE client connections and broadcasts operational events."""

    _subscribers: set[asyncio.Queue] = set()
    _event_history: list[SyncEventDTO] = []
    _event_counter: int = 0

    @classmethod
    def get_active_operators_count(cls) -> int:
        """Returns the current number of active connected control tower operator sessions."""
        return len(cls._subscribers)

    @classmethod
    async def subscribe(cls) -> AsyncGenerator[str, None]:
        """Registers an SSE client connection and yields formatted event-stream text."""
        q: asyncio.Queue = asyncio.Queue()
        cls._subscribers.add(q)
        try:
            # Yield initial connection heartbeat event
            yield "event: connected\ndata: {\"status\": \"CONNECTED\"}\n\n"
            while True:
                try:
                    # Wait for published events or periodic heartbeat
                    event: SyncEventDTO = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: sync_event\ndata: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat message keeping SSE connection alive
                    yield "event: heartbeat\ndata: {\"ping\": true}\n\n"
        finally:
            cls._subscribers.discard(q)

    @classmethod
    async def publish_event(
        cls,
        event_type: str,
        snapshot_version: str,
        details: dict[str, Any] | None = None
    ) -> SyncEventDTO:
        """Broadcasts an operational sync event to all connected operators."""
        cls._event_counter += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        evt = SyncEventDTO(
            event_id=f"EVT-SYNC-{cls._event_counter:04d}",
            event_type=event_type, # type: ignore
            timestamp=now_str,
            snapshot_version=snapshot_version,
            details=details or {},
        )

        cls._event_history.append(evt)
        if len(cls._event_history) > 100:
            cls._event_history.pop(0)

        # Broadcast to all registered client queues
        for q in list(cls._subscribers):
            await q.put(evt)

        return evt

    @classmethod
    def get_event_history(cls) -> list[SyncEventDTO]:
        """Returns recent sync events history."""
        return list(cls._event_history)
