"""Unit and integration tests for Operations Intelligence Console APIs."""

import pytest
from fastapi.testclient import TestClient


def test_overview_endpoint(client: TestClient):
    res = client.get("/api/v1/overview")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "kpis" in data
    assert "recent_incidents" in data
    assert "systems_summary" in data
    assert data["kpis"]["active_incidents"] >= 1
    assert data["kpis"]["estimated_revenue_impact"] > 0


def test_systems_endpoints(client: TestClient):
    # 1. List all systems
    res = client.get("/api/v1/systems")
    assert res.status_code == 200
    systems = res.json()
    assert len(systems) >= 5
    names = [s["name"] for s in systems]
    assert "checkout-service" in names
    assert "postgres-cluster" in names

    # 2. Detail for checkout-service
    res_det = client.get("/api/v1/systems/checkout-service")
    assert res_det.status_code == 200
    det = res_det.json()
    assert det["name"] == "checkout-service"
    assert "dependencies" in det
    assert "recent_deployments" in det
    assert "related_incidents" in det


def test_audit_logs_endpoint(client: TestClient):
    headers = {"X-User-Role": "ADMIN"}
    res = client.get("/api/v1/audit", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


def test_settings_endpoint(client: TestClient):
    headers = {"X-User-Role": "VIEWER"}
    res = client.get("/api/v1/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "Aegis" in data["app_name"]
    assert "ai_config" in data
    assert "data_policy" in data
    assert "retention_policy" in data


def test_search_endpoint(client: TestClient):
    res = client.get("/api/v1/search?q=checkout")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    types = [r["type"] for r in data["results"]]
    assert "incident" in types or "system" in types


def test_recommendations_endpoint(client: TestClient):
    headers = {"X-User-Role": "OPERATOR"}
    res = client.get("/api/v1/recommendations", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["title"] is not None


def test_investigations_global_list_endpoint(client: TestClient):
    headers = {"X-User-Role": "ANALYST"}
    res = client.get("/api/v1/investigations", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["status"] is not None
