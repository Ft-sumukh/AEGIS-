"""Tests for Service Level Objectives (SLO) & Multi-Window Error Budget Engine."""

import uuid

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.analytics.slo_service import SLOService
from app.database.session import get_db
from app.main import app
from app.models.company import Company
from app.models.slo import ServiceLevelObjective


def test_slo_listing_and_defaults(seeded_db_session: Session):
    """Verifies default SLOs are provisioned and retrieved via the API."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    response = client.get("/api/v1/slos", headers={"X-User-Role": "VIEWER", "X-Actor-Id": "sre@ops.com"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    services = [s["service_name"] for s in data]
    assert "checkout-service" in services
    assert "payment-service" in services
    assert "api-gateway" in services

    # Verify fields
    first = data[0]
    assert "burn_rate_1h" in first
    assert "burn_rate_6h" in first
    assert "burn_rate_24h" in first
    assert "error_budget_remaining_percent" in first
    assert "target_percentage" in first
    assert first["status"] in ("HEALTHY", "WARNING", "BURNING", "EXHAUSTED")


def test_slo_summary(seeded_db_session: Session):
    """Verifies the aggregate SLO summary statistics endpoint."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    response = client.get("/api/v1/slos/summary", headers={"X-User-Role": "VIEWER", "X-Actor-Id": "sre@ops.com"})
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_slos"] >= 5
    assert "healthy_count" in summary
    assert "average_error_budget_percent" in summary
    assert summary["average_error_budget_percent"] >= 0.0


def test_slo_evaluation_burn_rate(seeded_db_session: Session):
    """Verifies that simulating an elevated error rate triggers high burn rate & status transitions."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    # Fetch all SLOs to get an ID
    res = client.get("/api/v1/slos", headers={"X-User-Role": "VIEWER", "X-Actor-Id": "sre@ops.com"})
    slos = res.json()
    target_slo = slos[0]
    slo_id = target_slo["id"]

    # Trigger evaluation with normal error rate (0.01%)
    eval_res = client.post(
        f"/api/v1/slos/{slo_id}/evaluate",
        json={"override_recent_error_rate": 0.01},
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "sre@ops.com"},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["burn_rate_1h"] <= 1.5
    assert eval_data["status"] == "HEALTHY"

    # Trigger evaluation with critical error rate (5.0%) -> should exceed 14.4x burn rate paging threshold
    crit_res = client.post(
        f"/api/v1/slos/{slo_id}/evaluate",
        json={"override_recent_error_rate": 5.0},
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "sre@ops.com"},
    )
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert crit_data["burn_rate_1h"] >= 14.4
    assert crit_data["status"] == "BURNING"
    assert crit_data["time_to_exhaustion_hours"] is not None
    assert crit_data["time_to_exhaustion_hours"] > 0


def test_create_custom_slo(seeded_db_session: Session):
    """Verifies registering a custom enterprise SLO."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    payload = {
        "name": "Search & Recommendations Latency SLO",
        "service_name": "search-service",
        "description": "Ensures catalog indexing latency remains sub-50ms.",
        "target_percentage": 99.8,
        "sli_metric_name": "search_latency_p95",
        "sli_type": "LATENCY",
        "time_window_days": 14,
    }

    res = client.post(
        "/api/v1/slos",
        json=payload,
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "sre@ops.com"},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == payload["name"]
    assert created["service_name"] == "search-service"
    assert created["target_percentage"] == 99.8
    assert created["status"] == "HEALTHY"
