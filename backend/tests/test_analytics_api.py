"""Integration and contract tests for Analytics and Anomalies API endpoints."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.company import Company


def test_trigger_analytics_run_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    """POST /api/v1/analytics/run triggers analysis and returns execution summary."""
    company = seeded_db_session.query(Company).first()
    assert company is not None

    payload = {
        "company_id": str(company.id),
        "metric_filter": ["api_error_rate", "checkout_failure_rate", "revenue"],
    }

    response = client.post("/api/v1/analytics/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("COMPLETED", "RUNNING")
    assert data["company_id"] == str(company.id)
    assert "records_analyzed" in data
    assert "anomalies_detected" in data
    assert "incident_candidates_generated" in data


def test_get_analytics_status_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    """GET /api/v1/analytics/status returns recent execution audit history."""
    company = seeded_db_session.query(Company).first()
    assert company is not None

    # Trigger a run first
    client.post("/api/v1/analytics/run", json={"company_id": str(company.id)})

    response = client.get("/api/v1/analytics/status?limit=5")
    assert response.status_code == 200
    history = response.json()

    assert isinstance(history, list)
    assert len(history) >= 1
    assert "run_id" in history[0]
    assert "status" in history[0]


def test_get_incident_candidates_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    """GET /api/v1/incident-candidates returns correlated incident candidates with impact."""
    company = seeded_db_session.query(Company).first()
    assert company is not None

    # Run analysis
    client.post("/api/v1/analytics/run", json={"company_id": str(company.id)})

    response = client.get(f"/api/v1/incident-candidates?company_id={company.id}")
    assert response.status_code == 200
    candidates = response.json()

    assert isinstance(candidates, list)
    for c in candidates:
        assert "candidate_id" in c
        assert "title" in c
        assert "severity" in c
        assert "correlation_score" in c
        assert "impact" in c
        assert c["impact"]["is_preliminary"] is True


def test_list_anomalies_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    """GET /api/v1/anomalies returns paginated list of anomalies with filtering."""
    company = seeded_db_session.query(Company).first()
    assert company is not None

    response = client.get(f"/api/v1/anomalies?company_id={company.id}&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 10
    assert data["total"] >= 1


def test_get_anomaly_summary_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    """GET /api/v1/anomalies/summary returns aggregated counts."""
    company = seeded_db_session.query(Company).first()
    assert company is not None

    response = client.get(f"/api/v1/anomalies/summary?company_id={company.id}")
    assert response.status_code == 200
    summary = response.json()

    assert "total_anomalies" in summary
    assert "by_severity" in summary
    assert "by_status" in summary
    assert "by_detector_type" in summary
    assert "top_metrics" in summary
    assert summary["total_anomalies"] >= 1


def test_get_anomaly_by_id_endpoint(client: TestClient) -> None:
    """GET /api/v1/anomalies/{id} retrieves specific anomaly details."""
    # List first anomaly
    list_res = client.get("/api/v1/anomalies?limit=1")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) > 0
    anom_id = items[0]["id"]

    response = client.get(f"/api/v1/anomalies/{anom_id}")
    assert response.status_code == 200
    anomaly = response.json()

    assert anomaly["id"] == anom_id
    assert "metric_name" in anomaly
    assert "observed_value" in anomaly
    assert "expected_value" in anomaly
    assert "detector_type" in anomaly
    assert "confidence" in anomaly


def test_get_anomaly_by_id_not_found(client: TestClient) -> None:
    """GET /api/v1/anomalies/{id} returns 404 for non-existent UUID."""
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/anomalies/{fake_id}")
    assert response.status_code == 404
