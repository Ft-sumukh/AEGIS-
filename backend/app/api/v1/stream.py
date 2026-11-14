"""Server-Sent Events (SSE) streaming router for live operational alerts, anomalies, and actions."""

import asyncio
from collections.abc import AsyncGenerator
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.events import OperationalEvent, broadcast_event, event_bus
from app.security.auth import AuthUser, UserRole, require_role

logger = logging.getLogger("aegis.stream")

router = APIRouter(prefix="/stream", tags=["Streaming & Real-Time Alerts"])


class BroadcastRequest(BaseModel):
    event_type: str = Field(..., description="Type of event to broadcast")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload data")
    company_id: str | None = Field(None, description="Optional tenant company ID")


@router.get("/events", summary="Stream live operational events via SSE")
async def stream_events(
    request: Request,
    company_id: str | None = Query(None, description="Optional tenant company filter"),
) -> StreamingResponse:
    """Subscribes the client to a continuous Server-Sent Events stream.

    Streams:
    - HEARTBEAT (every 15 seconds)
    - ANOMALY_DETECTED
    - INCIDENT_CREATED / INCIDENT_ESCALATED / INCIDENT_RESOLVED
    - ACTION_PROPOSED / ACTION_APPROVED / ACTION_EXECUTED / ACTION_VERIFIED
    - CHAOS_FAULT_INJECTED / CHAOS_FAULT_RECOVERED
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send initial connected greeting
        init_event = OperationalEvent(
            event_type="CONNECTED",
            payload={"message": "Connected to Aegis Real-Time Operations Stream"},
            company_id=company_id,
        )
        yield init_event.to_sse_format()

        subscriber = event_bus.subscribe()
        try:
            while True:
                # Wait for next event or send heartbeat every 15s
                if await request.is_disconnected():
                    logger.debug("Client disconnected from SSE stream")
                    break

                try:
                    event = await asyncio.wait_for(subscriber.__anext__(), timeout=15.0)
                    if company_id and event.company_id and event.company_id != company_id:
                        continue
                    yield event.to_sse_format()
                except TimeoutError:
                    # Heartbeat frame
                    heartbeat = OperationalEvent(
                        event_type="HEARTBEAT",
                        payload={"status": "healthy"},
                        company_id=company_id,
                    )
                    yield heartbeat.to_sse_format()
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/broadcast", summary="Broadcast operational alert to all listeners")
async def broadcast_custom_event(
    req: BroadcastRequest,
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Allows an operator or admin to broadcast a high-priority operational notice."""
    event = await broadcast_event(
        event_type=req.event_type,
        payload={**req.data, "sender": user.user_id, "role": user.role.value},
        company_id=req.company_id,
    )
    return {
        "status": "success",
        "event_id": event.id,
        "type": event.event_type,
        "timestamp": event.timestamp,
    }


@router.get("/health", summary="Get real-time stream status")
async def stream_health() -> dict[str, Any]:
    """Returns subscriber count and stream health statistics."""
    return {
        "status": "active",
        "subscribers": len(event_bus._subscribers),
        "protocol": "Server-Sent Events (SSE)",
    }
