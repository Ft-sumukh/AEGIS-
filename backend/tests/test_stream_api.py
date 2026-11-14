"""Tests for the Real-time Event Streaming and SSE API endpoints."""

import pytest
from starlette.testclient import TestClient

from app.core.events import broadcast_event, event_bus
from app.main import app


def test_stream_health():
    client = TestClient(app)
    response = client.get("/api/v1/stream/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "subscribers" in data
    assert data["protocol"] == "Server-Sent Events (SSE)"


def test_broadcast_event_endpoint_rbac():
    client = TestClient(app)
    # Viewer role cannot broadcast (operator required)
    viewer_headers = {"X-User-Id": "test-viewer", "X-User-Role": "viewer"}
    res_forbidden = client.post(
        "/api/v1/stream/broadcast",
        json={"event_type": "TEST_ALERT", "data": {"msg": "hello"}},
        headers=viewer_headers,
    )
    assert res_forbidden.status_code == 403

    # Operator role can broadcast
    operator_headers = {"X-User-Id": "test-operator", "X-User-Role": "operator"}
    res_success = client.post(
        "/api/v1/stream/broadcast",
        json={"event_type": "MANUAL_ALERT", "data": {"priority": "CRITICAL"}},
        headers=operator_headers,
    )
    assert res_success.status_code == 200
    body = res_success.json()
    assert body["status"] == "success"
    assert body["type"] == "MANUAL_ALERT"


@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    test_event_type = "TEST_INTEGRATION_EVENT"
    received_events = []

    async def reader():
        subscriber = event_bus.subscribe()
        try:
            event = await subscriber.__anext__()
            received_events.append(event)
        finally:
            pass

    import asyncio

    reader_task = asyncio.create_task(reader())
    await asyncio.sleep(0.01)

    await broadcast_event(test_event_type, {"metric": "latency", "val": 450})
    await asyncio.wait_for(reader_task, timeout=2.0)

    assert len(received_events) == 1
    assert received_events[0].event_type == test_event_type
    assert received_events[0].payload["val"] == 450
