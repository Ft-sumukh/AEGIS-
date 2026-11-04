"""Unit tests for server-side Role-Based Access Control (RBAC)."""

import uuid
from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.company import Company
from app.models.incident import Incident
from app.models.enums import CompanyStatus, IncidentStatus, SeverityLevel


@pytest.fixture
def test_incident(db_session) -> Incident:
    company = Company(
        id=uuid.uuid4(),
        name="Security RBAC Test Corp",
        slug=f"rbac-test-{uuid.uuid4().hex[:6]}",
        industry="Technology",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Security Test Incident",
        summary="Testing server-side authorization gates",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        category="DATABASE",
        affected_systems=["db-replica"],
        affected_metrics=["db_query_time"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    return incident


def test_viewer_access_to_read_endpoints(client: TestClient, test_incident: Incident):
    headers = {"X-User-Role": "VIEWER"}
    # 1. Viewer can list incidents
    res = client.get("/api/v1/incidents", headers=headers)
    assert res.status_code == 200

    # 2. Viewer can inspect single incident
    res = client.get(f"/api/v1/incidents/{test_incident.id}", headers=headers)
    assert res.status_code == 200

    # 3. Viewer can view timeline
    res = client.get(f"/api/v1/incidents/{test_incident.id}/timeline", headers=headers)
    assert res.status_code == 200


def test_viewer_forbidden_from_privileged_mutations(client: TestClient, test_incident: Incident):
    headers = {"X-User-Role": "VIEWER"}

    # 1. Viewer cannot acknowledge incident -> 403
    ack_res = client.post(
        f"/api/v1/incidents/{test_incident.id}/acknowledge",
        json={"notes": "Viewer attempting acknowledgement"},
        headers=headers,
    )
    assert ack_res.status_code == 403

    # 2. Viewer cannot trigger AI investigation -> 403
    inv_res = client.post(
        f"/api/v1/incidents/{test_incident.id}/investigate",
        headers=headers,
    )
    assert inv_res.status_code == 403

    # 3. Viewer cannot create manual incident -> 403
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "company_id": str(test_incident.company_id),
            "title": "Unauthorized Incident",
            "summary": "Should be forbidden",
            "severity": "HIGH",
            "category": "API",
            "affected_systems": ["api"],
            "affected_metrics": ["error_rate"],
        },
        headers=headers,
    )
    assert create_res.status_code == 403


def test_analyst_can_trigger_investigation_but_cannot_acknowledge(client: TestClient, test_incident: Incident):
    headers = {"X-User-Role": "ANALYST"}

    # 1. Analyst cannot acknowledge incident -> 403
    ack_res = client.post(
        f"/api/v1/incidents/{test_incident.id}/acknowledge",
        json={"notes": "Analyst attempting acknowledgement"},
        headers=headers,
    )
    assert ack_res.status_code == 403

    # 2. Analyst CAN trigger AI investigation -> 201
    inv_res = client.post(
        f"/api/v1/incidents/{test_incident.id}/investigate",
        headers=headers,
    )
    assert inv_res.status_code == 201
    data = inv_res.json()
    assert data["incident_id"] == str(test_incident.id)
    assert data["status"] in ("COMPLETED", "RUNNING", "INSUFFICIENT_EVIDENCE")


def test_operator_can_acknowledge_and_update(client: TestClient, test_incident: Incident):
    headers = {"X-User-Role": "OPERATOR"}

    ack_res = client.post(
        f"/api/v1/incidents/{test_incident.id}/acknowledge",
        json={"transition_to_investigating": True},
        headers=headers,
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "INVESTIGATING"


def test_admin_has_full_operational_access(client: TestClient, test_incident: Incident):
    headers = {"X-User-Role": "ADMIN"}

    res = client.get(f"/api/v1/incidents/{test_incident.id}", headers=headers)
    assert res.status_code == 200
