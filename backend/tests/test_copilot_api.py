"""Tests for Incident Commander AI Co-Pilot API."""

from datetime import UTC, datetime
from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.company import Company
from app.models.enums import HypothesisStatus, IncidentStatus, InvestigationStatus, SeverityLevel
from app.models.incident import Incident
from app.models.investigation import Investigation, InvestigationHypothesis


@pytest.fixture
def copilot_incident(seeded_db_session: Session) -> Incident:
    company = seeded_db_session.query(Company).first()
    if not company:
        company = Company(id=uuid.uuid4(), name="Test Corp", slug="copilot-test-corp")
        seeded_db_session.add(company)
        seeded_db_session.flush()

    inc = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Database Connection Exhaustion in Checkout",
        summary="Checkout connection pool exhausted causing 504 gateway timeouts.",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.INVESTIGATING,
        category="DATABASE_EXHAUSTION",
        affected_systems=["checkout-service", "postgres-primary"],
        affected_metrics=["db_connection_count", "checkout_error_rate"],
        detected_at=datetime.now(UTC),
        estimated_revenue_impact=Decimal("25000.00"),
        estimated_users_affected=850,
        incident_metadata={},
    )
    seeded_db_session.add(inc)
    seeded_db_session.flush()

    inv = Investigation(
        id=uuid.uuid4(),
        incident_id=inc.id,
        status=InvestigationStatus.RUNNING,
        summary="Automated telemetry investigation confirms Postgres connection pool saturation.",
    )
    seeded_db_session.add(inv)
    seeded_db_session.flush()

    hyp1 = InvestigationHypothesis(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Postgres Max Connections Reached",
        description="Active pool connections exceeded max pool size.",
        status=HypothesisStatus.SUPPORTED,
        confidence=0.94,
        supporting_evidence_summary="pg_stat_activity shows 500 active idle-in-transaction connections.",
    )
    hyp2 = InvestigationHypothesis(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Network Partition to Redis",
        description="Redis latency probe check.",
        status=HypothesisStatus.REJECTED,
        confidence=0.12,
        supporting_evidence_summary="Redis ping latency is 0.4ms nominal.",
    )
    seeded_db_session.add_all([hyp1, hyp2])
    seeded_db_session.commit()
    return inc


def test_copilot_general_overview(seeded_db_session: Session):
    """Verifies default briefing overview response."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Give me an operational status briefing"},
        headers={"X-User-Role": "VIEWER", "X-Actor-Id": "commander@ops.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "Active Incidents" in data["reply"]
    assert len(data["suggested_prompts"]) > 0


def test_copilot_announcement_drafting(seeded_db_session: Session, copilot_incident: Incident):
    """Verifies that the Co-Pilot can draft StatusPage and Slack announcements."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Draft a status page announcement for this incident",
            "incident_id": str(copilot_incident.id),
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "commander@ops.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "ANNOUNCEMENT"
    assert "draft_payload" in data
    assert "INVESTIGATING" in data["draft_payload"]["title"]
    assert "checkout-service" in data["draft_payload"]["title"]


def test_copilot_root_cause_explanation(seeded_db_session: Session, copilot_incident: Incident):
    """Verifies hypothesis and evidence explanation capabilities."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Explain the root cause and rejected hypotheses",
            "incident_id": str(copilot_incident.id),
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "commander@ops.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "EXPLANATION"
    assert "Postgres Max Connections Reached" in data["reply"]
    assert "SUPPORTED" in data["reply"]
    assert "REJECTED" in data["reply"]


def test_copilot_runbook_mitigations(seeded_db_session: Session, copilot_incident: Incident):
    """Verifies SRE runbook suggestions and action safety reminders."""
    app.dependency_overrides[get_db] = lambda: seeded_db_session
    client = TestClient(app)

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "What runbooks should we run to fix this?",
            "incident_id": str(copilot_incident.id),
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Id": "commander@ops.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "MITIGATION"
    assert "Governance Safeguard" in data["reply"]
