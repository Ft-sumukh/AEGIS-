"""Tests for AI Post-Mortem and Retrospective generation and export."""

from datetime import UTC, datetime
from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.company import Company
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.services.postmortem_service import PostMortemService


@pytest.fixture
def sample_incident(seeded_db_session: Session) -> Incident:
    company = seeded_db_session.query(Company).first()
    if not company:
        company = Company(id=uuid.uuid4(), name="Test PIR Corp", slug="pir-corp")
        seeded_db_session.add(company)
        seeded_db_session.flush()

    inc = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Payment Gateway Timeout Outage",
        summary="Checkout failure rate spiked to 38% due to payment gateway timeouts.",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.RESOLVED,
        category="PAYMENT_FAILURE",
        affected_systems=["payment-service", "checkout-service"],
        affected_metrics=["checkout_error_rate", "payment_p99_latency"],
        detected_at=datetime.now(UTC),
        acknowledged_at=datetime.now(UTC),
        acknowledged_by="alice@ops.com",
        resolved_at=datetime.now(UTC),
        resolved_by="bob@ops.com",
        resolution_summary="Rolled back deployment v2.4.1 to restore payment connectivity.",
        estimated_revenue_impact=Decimal("45000.00"),
        estimated_orders_affected=320,
        estimated_users_affected=1500,
        incident_metadata={},
    )
    seeded_db_session.add(inc)
    seeded_db_session.commit()
    return inc


def test_postmortem_service_generation(seeded_db_session: Session, sample_incident: Incident):
    pir = PostMortemService.generate_postmortem(seeded_db_session, sample_incident, author="Test AI")
    assert pir["postmortem_id"].startswith("PIR-")
    assert pir["incident_id"] == str(sample_incident.id)
    assert pir["severity"] == "CRITICAL"
    assert pir["metrics"]["mttd_seconds"] > 0
    assert pir["blast_radius"]["estimated_revenue_lost"] == 45000.0
    assert len(pir["five_whys"]) == 5
    assert len(pir["preventative_action_items"]) == 3

    # Check markdown rendering
    md = PostMortemService.render_markdown(pir)
    assert "# Post-Incident Review: Payment Gateway Timeout Outage" in md
    assert "The 5 Whys" in md
    assert "Preventative Action Items" in md


def test_postmortem_endpoints(client: TestClient, sample_incident: Incident):
    # Operator generates postmortem
    headers = {"X-User-Role": "operator", "X-User-Id": "ops-lead"}
    res = client.post(f"/api/v1/incidents/{sample_incident.id}/postmortem", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == str(sample_incident.id)
    assert "five_whys" in data

    # Viewer reads postmortem
    viewer_headers = {"X-User-Role": "viewer"}
    res_get = client.get(f"/api/v1/incidents/{sample_incident.id}/postmortem", headers=viewer_headers)
    assert res_get.status_code == 200
    assert res_get.json()["title"] == data["title"]

    # Export markdown
    res_md = client.get(f"/api/v1/incidents/{sample_incident.id}/postmortem/markdown", headers=viewer_headers)
    assert res_md.status_code == 200
    assert res_md.headers["content-type"].startswith("text/markdown")
    assert "# Post-Incident Review:" in res_md.text
