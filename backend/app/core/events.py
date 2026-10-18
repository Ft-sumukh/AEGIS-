"""Real-time event broadcasting and in-memory Pub/Sub engine for Aegis live telemetry and alert streams."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
import json
import logging
from typing import Any
import uuid

logger = logging.getLogger("aegis.events")


class OperationalEvent:
    """Represents a discrete real-time operational event streamed across Aegis."""

    def __init__(
        self,
        event_type: str,
        payload: dict[str, Any],
        company_id: str | None = None,
        event_id: str | None = None,
    ):
        self.id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.company_id = company_id
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type,
            "timestamp": self.timestamp,
            "company_id": self.company_id,
            "data": self.payload,
        }

    def to_sse_format(self) -> str:
        """Formats the event as a standard Server-Sent Event (SSE) frame."""
        data_json = json.dumps(self.to_dict(), default=str)
        return f"event: {self.event_type}\nid: {self.id}\ndata: {data_json}\n\n"


class EventBus:
    """Thread-safe asyncio Pub/Sub event bus for live streaming."""

    def __init__(self, max_subscribers: int = 200, queue_size: int = 100):
        self._subscribers: set[asyncio.Queue[OperationalEvent]] = set()
        self._lock = asyncio.Lock()
        self._max_subscribers = max_subscribers
        self._queue_size = queue_size

    async def subscribe(self) -> AsyncGenerator[OperationalEvent, None]:
        """Subscribe to the operational event stream."""
        queue: asyncio.Queue[OperationalEvent] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            if len(self._subscribers) >= self._max_subscribers:
                # Evict oldest or reject if saturated
                logger.warning("EventBus maximum subscriber limit reached")
            self._subscribers.add(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def broadcast(
        self,
        event_type: str,
        payload: dict[str, Any],
        company_id: str | None = None,
    ) -> OperationalEvent:
        """Broadcasts an event to all connected subscriber queues."""
        event = OperationalEvent(
            event_type=event_type,
            payload=payload,
            company_id=company_id,
        )

        async with self._lock:
            dead_queues = []
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop slow client queue or evict
                    dead_queues.append(queue)

            for dead in dead_queues:
                self._subscribers.discard(dead)

        logger.debug(
            "Broadcasted event %s to %d subscribers",
            event_type,
            len(self._subscribers),
        )
        return event

    def broadcast_sync(
        self,
        event_type: str,
        payload: dict[str, Any],
        company_id: str | None = None,
    ) -> None:
        """Helper to fire-and-forget broadcast from synchronous code without blocking."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(event_type, payload, company_id))
        except RuntimeError:
            # No running loop in synchronous thread/test context
            pass


# Global singleton instance
event_bus = EventBus()


async def broadcast_event(
    event_type: str,
    payload: dict[str, Any],
    company_id: str | None = None,
) -> OperationalEvent:
    """Global convenience helper to broadcast an event."""
    return await event_bus.broadcast(event_type, payload, company_id)


def broadcast_event_sync(
    event_type: str,
    payload: dict[str, Any],
    company_id: str | None = None,
) -> None:
    """Global convenience helper to broadcast an event synchronously."""
    event_bus.broadcast_sync(event_type, payload, company_id)
