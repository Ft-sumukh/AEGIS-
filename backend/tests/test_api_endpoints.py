"""Integration tests for collection and detail API endpoints."""

import uuid

from fastapi.testclient import TestClient


def test_list_metrics_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/metrics returns seeded metrics with pagination."""
    response = client.get("/api/v1/metrics?limit=10&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] > 0
    assert len(data["items"]) <= 10

    # Filter by metric_name
    filtered_res = client.get("/api/v1/metrics?metric_name=checkout_failure_rate")
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    assert filtered_data["total"] >= 1
    for item in filtered_data["items"]:
        assert item["metric_name"] == "checkout_failure_rate"


def test_list_anomalies_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/anomalies returns detected anomalies with filtering."""
    response = client.get("/api/v1/anomalies")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 2
    anomaly = data["items"][0]
    assert "detected_at" in anomaly
    assert "observed_value" in anomaly
    assert "detector_type" in anomaly

    # Filter by severity
    crit_res = client.get("/api/v1/anomalies?severity=CRITICAL")
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert crit_data["total"] >= 1
    for item in crit_data["items"]:
        assert item["severity"] == "CRITICAL"


def test_list_incidents_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/incidents returns incidents."""
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    incident = data["items"][0]
    assert "title" in incident
    assert "severity" in incident
    assert "status" in incident


def test_get_incident_detail_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/incidents/{id} returns detailed incident with nested evidence and anomalies."""
    list_res = client.get("/api/v1/incidents")
    incident_id = list_res.json()["items"][0]["id"]

    detail_res = client.get(f"/api/v1/incidents/{incident_id}")
    assert detail_res.status_code == 200

    detail = detail_res.json()
    assert detail["id"] == incident_id
    assert "anomalies" in detail
    assert "evidence" in detail
    assert len(detail["anomalies"]) >= 1
    assert len(detail["evidence"]) >= 1


def test_get_incident_404(client: TestClient) -> None:
    """Verify GET /api/v1/incidents/{id} returns 404 for non-existent incident."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/incidents/{random_id}")
    assert response.status_code == 404
    error_payload = response.json()
    assert "detail" in error_payload
    assert "was not found" in error_payload["detail"]


def test_safe_error_masking(client: TestClient, monkeypatch) -> None:
    """Verify database exceptions do not expose raw SQL or internal traceback to client."""
    from app.services.incident_service import IncidentService

    def mock_raise(*_args, **_kwargs):
        raise RuntimeError("CRITICAL: SELECT * FROM secret_table WHERE password='leak';")

    monkeypatch.setattr(IncidentService, "list_incidents", mock_raise)

    response = client.get("/api/v1/incidents")
    assert response.status_code == 500
    data = response.json()
    assert "secret_table" not in str(data)
    assert "password" not in str(data)
    assert data["detail"] == "An error occurred while retrieving operational incidents."
