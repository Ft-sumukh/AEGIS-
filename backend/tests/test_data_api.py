"""Integration tests for telemetry data source, summary, and quality endpoints."""

from fastapi.testclient import TestClient


def test_data_sources_endpoint(client: TestClient) -> None:
    """Verifies GET /api/v1/data/sources returns operational data sources and metadata."""
    response = client.get("/api/v1/data/sources")
    assert response.status_code == 200

    data = response.json()
    assert data["classification"] == "PUBLIC_DEMO"
    assert "CSV" in data["supported_formats"]
    assert "JSON" in data["supported_formats"]
    assert "active_telemetry_sources" in data
    assert "checkout-service" in data["registered_services"]
    assert data["status"] == "HEALTHY"


def test_data_summary_endpoint(client: TestClient) -> None:
    """Verifies GET /api/v1/data/summary returns aggregate entity counts."""
    response = client.get("/api/v1/data/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "READY"
    assert "counts" in data
    assert "companies" in data["counts"]
    assert "customers" in data["counts"]
    assert "orders" in data["counts"]
    assert "operational_metrics" in data["counts"]
    assert "deployments" in data["counts"]
    assert "system_events" in data["counts"]
    assert "support_tickets" in data["counts"]
    assert "customer_complaints" in data["counts"]
    assert "time_horizon" in data


def test_data_quality_endpoint(client: TestClient) -> None:
    """Verifies GET /api/v1/data/quality returns data quality metrics and privacy assurance."""
    response = client.get("/api/v1/data/quality")
    assert response.status_code == 200

    data = response.json()
    assert data["overall_health"] == "PASSED"
    assert data["data_classification"] == "PUBLIC_DEMO"
    assert data["privacy_compliance"]["real_pii_detected"] is False
    assert data["privacy_compliance"]["email_domains"] == "SYNTHETIC_ONLY (*@example.com)"
    assert data["quality_metrics"]["idempotency_compliance"] == "ENFORCED"
