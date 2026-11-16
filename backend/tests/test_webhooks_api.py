"""Tests for External Webhook Subscriptions and Alert Dispatcher API."""

import uuid

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.company import Company
from app.webhooks.dispatcher import WebhookDispatcher


def test_create_and_list_webhooks(seeded_db_session: Session):
    """Verifies creating and listing webhook subscriptions."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    payload = {
        "name": "Slack Operations Channel",
        "url": "https://notifications.internal/services/slack-channel-alert",
        "secret_token": "mock-test-secret-token",
        "target_type": "SLACK",
        "subscribed_events": ["INCIDENT_CREATED", "SLO_BUDGET_BURNING"],
    }

    create_res = client.post(
        "/api/v1/webhooks",
        json=payload,
        headers={"X-User-Role": "ADMIN", "X-Actor-Id": "admin@ops.com"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == payload["name"]
    assert created["target_type"] == "SLACK"
    assert "id" in created

    # List webhooks
    list_res = client.get(
        "/api/v1/webhooks",
        headers={"X-User-Role": "VIEWER", "X-Actor-Id": "admin@ops.com"},
    )
    assert list_res.status_code == 200
    subs = list_res.json()
    assert any(s["id"] == created["id"] for s in subs)


def test_test_webhook_dispatch(seeded_db_session: Session):
    """Verifies sending a test verification probe to a registered webhook."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    # Register PagerDuty webhook
    create_res = client.post(
        "/api/v1/webhooks",
        json={
            "name": "PagerDuty SRE High Sev",
            "url": "https://events.pagerduty.com/v2/enqueue",
            "target_type": "PAGERDUTY",
            "subscribed_events": ["INCIDENT_CREATED"],
        },
        headers={"X-User-Role": "ADMIN", "X-Actor-Id": "admin@ops.com"},
    )
    assert create_res.status_code == 201
    webhook_id = create_res.json()["id"]

    # Trigger test probe
    test_res = client.post(
        f"/api/v1/webhooks/{webhook_id}/test",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "admin@ops.com"},
    )
    assert test_res.status_code == 200
    res_data = test_res.json()
    assert res_data["status"] == "DELIVERED"
    assert res_data["status_code"] == 200
    assert "payload_preview" in res_data
    assert res_data["payload_preview"]["event_action"] == "trigger"


def test_delete_webhook(seeded_db_session: Session):
    """Verifies deleting a webhook subscription."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    create_res = client.post(
        "/api/v1/webhooks",
        json={
            "name": "Temporary Hook",
            "url": "https://example.com/webhook",
            "target_type": "GENERIC_WEBHOOK",
        },
        headers={"X-User-Role": "ADMIN", "X-Actor-Id": "admin@ops.com"},
    )
    webhook_id = create_res.json()["id"]

    del_res = client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-User-Role": "ADMIN", "X-Actor-Id": "admin@ops.com"},
    )
    assert del_res.status_code == 200

    # Ensure 404 when tested
    test_res = client.post(
        f"/api/v1/webhooks/{webhook_id}/test",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "admin@ops.com"},
    )
    assert test_res.status_code == 404
