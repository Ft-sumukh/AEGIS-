"""Unit tests for Incident creation from candidate and manual operator creation."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.models import BusinessImpactEstimate, IncidentCandidate
from app.incidents.creation import IncidentCreationService, infer_category_and_systems
from app.models.anomaly import Anomaly
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.enums import (
    AnomalyStatus,
    CompanyStatus,
    DetectorType,
    IncidentStatus,
    SeverityLevel,
)


@pytest.fixture
def test_company(db_session: Session) -> Company:
    company = Company(
        id=uuid.uuid4(),
        name="Acme Operations",
        slug=f"acme-ops-{uuid.uuid4().hex[:6]}",
        industry="E-Commerce",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()
    return company


def test_infer_category_and_systems() -> None:
    cat, sys = infer_category_and_systems(["checkout_failure_rate", "payment_error_rate"])
    assert cat == "CHECKOUT"
    assert "checkout-service" in sys

    cat, sys = infer_category_and_systems(["api_latency", "error_rate_5xx"])
    assert cat == "API"
    assert "api-gateway" in sys

    cat, sys = infer_category_and_systems(["db_connection_pool"])
    assert cat == "DATABASE"
    assert "postgres-cluster" in sys


def test_create_from_candidate(db_session: Session, test_company: Company) -> None:
    now = datetime.now(UTC)
    anom1 = Anomaly(
        id=uuid.uuid4(),
        company_id=test_company.id,
        metric_name="checkout_failure_rate",
        detector_type=DetectorType.Z_SCORE,
        severity=SeverityLevel.CRITICAL,
        status=AnomalyStatus.NEW,
        deviation=4.5,
        observed_value=42.5,
        expected_value=1.2,
        confidence=0.95,
        explanation="Anomalous spike in checkout failure rate",
        detected_at=now,
    )
    db_session.add(anom1)
    db_session.flush()

    candidate = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=test_company.id,
        title="High Checkout Failure Cluster",
        preliminary_summary="Observed elevated checkout failures",
        severity=SeverityLevel.CRITICAL,
        correlation_score=0.92,
        first_detected_at=now,
        last_detected_at=now + timedelta(minutes=15),
        affected_metrics=["checkout_failure_rate"],
        anomaly_ids=[anom1.id],
        impact=BusinessImpactEstimate(
            estimated_revenue_impact=Decimal("3500.00"),
            estimated_orders_affected=65,
            estimated_users_affected=120,
            additional_support_tickets=8,
            additional_complaints=4,
        ),
    )

    incident, is_new = IncidentCreationService.create_from_candidate(
        db=db_session,
        candidate=candidate,
        actor="system",
    )

    assert is_new is True
    assert incident.company_id == test_company.id
    assert incident.status == IncidentStatus.OPEN
    assert incident.severity == SeverityLevel.CRITICAL
    assert incident.category == "CHECKOUT"
    assert "checkout_failure_rate" in incident.affected_metrics
    assert incident.estimated_orders_affected == 65
    assert incident.estimated_support_impact == 12
    assert len(incident.anomalies) == 1
    assert len(incident.evidence) >= 1

    # Check audit log
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.resource_id == str(incident.id),
            AuditLog.action == "INCIDENT_CREATED",
        )
    )
    assert audit is not None
    assert audit.audit_metadata["creation_mode"] == "FROM_CANDIDATE"


def test_create_from_candidate_deduplication(db_session: Session, test_company: Company) -> None:
    now = datetime.now(UTC)
    candidate = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=test_company.id,
        title="Payment Gateway Timeout",
        preliminary_summary="Payment gateway timeout",
        severity=SeverityLevel.HIGH,
        correlation_score=0.85,
        first_detected_at=now,
        last_detected_at=now + timedelta(minutes=10),
        affected_metrics=["payment_timeout_rate"],
        anomaly_ids=[],
    )

    inc1, is_new1 = IncidentCreationService.create_from_candidate(
        db=db_session, candidate=candidate
    )
    assert is_new1 is True

    # Same candidate within the same temporal window
    inc2, is_new2 = IncidentCreationService.create_from_candidate(
        db=db_session, candidate=candidate
    )
    assert is_new2 is False
    assert inc1.id == inc2.id


def test_create_manual_incident(db_session: Session, test_company: Company) -> None:
    incident = IncidentCreationService.create_manual_incident(
        db=db_session,
        company_id=test_company.id,
        title="Manual Third-Party Outage",
        summary="External payment gateway experiencing global latency spike",
        severity=SeverityLevel.HIGH,
        category="PAYMENT",
        affected_systems=["payment-provider", "billing"],
        affected_metrics=["payment_latency"],
        tags=["external-dependency", "p0"],
        owner_id="oncall-eng-1",
        team_name="core-infra",
        initial_note="Escalated to vendor support at 14:02 UTC.",
        actor="alice_ops",
    )

    assert incident.id is not None
    assert incident.status == IncidentStatus.OPEN
    assert incident.severity == SeverityLevel.HIGH
    assert incident.owner_id == "oncall-eng-1"
    assert incident.team_name == "core-infra"
    assert len(incident.notes) == 1
    assert incident.notes[0].author == "alice_ops"
    assert "Escalated to vendor" in incident.notes[0].text
