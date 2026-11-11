"""Integration tests for all /api/v1/incidents API endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import IncidentStatus
from app.models.incident import Incident


def test_list_incidents_filtering_and_pagination(client: TestClient) -> None:
    # Seeded database contains at least 1 incident
    res = client.get("/api/v1/incidents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Filter by status
    res_status = client.get("/api/v1/incidents?status=INVESTIGATING")
    assert res_status.status_code == 200
    for item in res_status.json()["items"]:
        assert item["status"] == "INVESTIGATING"

    # Filter by non-matching status
    res_closed = client.get("/api/v1/incidents?status=CLOSED")
    assert res_closed.status_code == 200
    assert res_closed.json()["total"] == 0


def test_create_manual_incident_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    payload = {
        "company_id": str(company.id),
        "title": "Database Read Replicas Out of Sync",
        "summary": "Replication lag exceeded 60 seconds on read replicas.",
        "severity": "HIGH",
        "category": "DATABASE",
        "affected_systems": ["postgres-replica-1", "postgres-replica-2"],
        "affected_metrics": ["replication_lag_seconds"],
        "tags": ["database", "replication"],
        "owner_id": "dba_team",
        "initial_note": "Failover initiated at 10:15.",
    }

    res = client.post("/api/v1/incidents?actor=dba_dan", json=payload)
    assert res.status_code == 201
    incident = res.json()
    assert incident["title"] == payload["title"]
    assert incident["severity"] == "HIGH"
    assert incident["category"] == "DATABASE"
    assert incident["status"] == "OPEN"
    assert len(incident["notes"]) == 1
    assert incident["notes"][0]["author"] == "dba_dan"


def test_create_from_candidate_endpoint(client: TestClient, seeded_db_session: Session) -> None:
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    cand_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    payload = {
        "candidate_id": cand_id,
        "company_id": str(company.id),
        "title": "Autonomous Candidate Cluster",
        "preliminary_summary": "Correlation detected anomalous payment drops",
        "severity": "CRITICAL",
        "correlation_score": 0.94,
        "first_detected_at": now,
        "last_detected_at": now,
        "affected_metrics": ["checkout_failure_rate", "payment_error_rate"],
        "anomaly_ids": [],
        "estimated_revenue_impact": 4500.0,
        "estimated_orders_affected": 80,
        "estimated_users_affected": 150,
    }

    # First creation -> 201
    res1 = client.post("/api/v1/incidents/from-candidate?actor=system", json=payload)
    assert res1.status_code == 201
    inc1 = res1.json()
    assert inc1["severity"] in ("HIGH", "CRITICAL")
    assert inc1["category"] == "CHECKOUT"

    # Subsequent creation of duplicate candidate -> 200
    res2 = client.post("/api/v1/incidents/from-candidate?actor=system", json=payload)
    assert res2.status_code == 200
    inc2 = res2.json()
    assert inc1["id"] == inc2["id"]


def test_incident_lifecycle_endpoints(client: TestClient, seeded_db_session: Session) -> None:
    incident = seeded_db_session.scalar(
        select(Incident).where(Incident.status == IncidentStatus.INVESTIGATING).limit(1)
    )
    assert incident is not None
    inc_id = str(incident.id)

    # 1. Acknowledge
    ack_res = client.post(
        f"/api/v1/incidents/{inc_id}/acknowledge?actor=operator_sue",
        json={"transition_to_investigating": False},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged_by"] == "operator_sue"

    # 2. Transition INVESTIGATING -> MITIGATED
    mit_res = client.post(
        f"/api/v1/incidents/{inc_id}/status?actor=operator_sue",
        json={"status": "MITIGATED", "reason": "Rolled back faulty release"},
    )
    assert mit_res.status_code == 200
    assert mit_res.json()["status"] == "MITIGATED"

    # 3. Transition MITIGATED -> RESOLVED without summary -> 400 Bad Request
    inv_res = client.post(
        f"/api/v1/incidents/{inc_id}/status?actor=operator_sue",
        json={"status": "RESOLVED", "resolution_summary": ""},
    )
    assert inv_res.status_code == 400

    # 4. Transition MITIGATED -> RESOLVED with valid summary -> 200
    res_res = client.post(
        f"/api/v1/incidents/{inc_id}/status?actor=operator_sue",
        json={
            "status": "RESOLVED",
            "resolution_summary": "Issue resolved by database connection pool reload.",
        },
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["resolved_by"] == "operator_sue"

    # 5. Transition RESOLVED -> CLOSED -> 200
    close_res = client.post(
        f"/api/v1/incidents/{inc_id}/status?actor=manager_tom",
        json={"status": "CLOSED", "closed_by": "manager_tom"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"

    # 6. Attempt reopen from CLOSED -> 400 Bad Request
    reopen_res = client.post(
        f"/api/v1/incidents/{inc_id}/status?actor=manager_tom",
        json={"status": "OPEN"},
    )
    assert reopen_res.status_code == 400


def test_incident_evidence_notes_and_timeline_endpoints(
    client: TestClient, seeded_db_session: Session
) -> None:
    incident = seeded_db_session.scalar(select(Incident).limit(1))
    assert incident is not None
    inc_id = str(incident.id)

    # 1. Add Note
    note_res = client.post(
        f"/api/v1/incidents/{inc_id}/notes",
        json={"author": "lead_eng", "text": "Contacted payment processor partner."},
    )
    assert note_res.status_code == 201
    assert note_res.json()["author"] == "lead_eng"

    # 2. List Notes
    notes_list_res = client.get(f"/api/v1/incidents/{inc_id}/notes")
    assert notes_list_res.status_code == 200
    assert len(notes_list_res.json()) >= 1

    # 3. Add Evidence
    ev_payload = {
        "source_type": "SYSTEM_EVENT",
        "source_id": str(uuid.uuid4()),
        "title": "CPU Throttle Alert",
        "summary": "Container CPU throttling reached 85% limit.",
        "observed_at": incident.detected_at.isoformat(),
        "severity": "HIGH",
    }
    ev_res = client.post(f"/api/v1/incidents/{inc_id}/evidence?actor=sre_lead", json=ev_payload)
    assert ev_res.status_code == 201
    assert ev_res.json()["title"] == ev_payload["title"]
    assert ev_res.json()["relevance_score"] >= 0.7

    # 4. List Evidence
    ev_list_res = client.get(f"/api/v1/incidents/{inc_id}/evidence")
    assert ev_list_res.status_code == 200
    assert len(ev_list_res.json()) >= 1

    # 5. Timeline
    tl_res = client.get(f"/api/v1/incidents/{inc_id}/timeline?ascending=true")
    assert tl_res.status_code == 200
    timeline = tl_res.json()
    assert len(timeline) >= 2

    # 6. Correlation View
    corr_res = client.get(f"/api/v1/incidents/{inc_id}/correlation")
    assert corr_res.status_code == 200
    corr = corr_res.json()
    assert corr["incident_id"] == inc_id
    assert "affected_metrics" in corr
