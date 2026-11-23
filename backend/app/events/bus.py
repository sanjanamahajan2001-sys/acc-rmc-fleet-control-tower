"""
EventBus Pub/Sub Subsystem

Provides abstract EventBus interface and in-memory/Redis pub/sub implementations
for publishing and subscribing to platform internal BaseEvent envelopes.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger
from app.events.schema import BaseEvent

logger = get_logger("app.events.bus")

EventHandler = Callable[[BaseEvent[Any]], Awaitable[None]]


class EventBus(ABC):
    """
    Abstract EventBus interface decoupling pub/sub logic from specific message brokers.
    """

    @abstractmethod
    async def publish(self, event: BaseEvent[Any]) -> None:
        """Publishes an event envelope to all subscribed handlers."""

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribes an async handler function to an event_type."""

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribes a handler function from an event_type."""


class InMemoryEventBus(EventBus):
    """
    In-memory async EventBus implementation for testing and single-node processing.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.info("Subscribed handler to event", event_type=event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.info("Unsubscribed handler from event", event_type=event_type)

    async def publish(self, event: BaseEvent[Any]) -> None:
        handlers = self._handlers.get(event.event_type, [])
        logger.info(
            "Publishing event to handlers",
            event_type=event.event_type,
            event_id=event.event_id,
            handler_count=len(handlers),
        )
        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Error executing event handler",
                    event_type=event.event_type,
                    event_id=event.event_id,
                    error=str(exc),
                )


# Global platform event bus instance
event_bus: EventBus = InMemoryEventBus()
