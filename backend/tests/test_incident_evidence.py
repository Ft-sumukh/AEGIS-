"""Unit tests for IncidentEvidence management, deterministic relevance scoring, and deduplication."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.incidents.evidence import IncidentEvidenceService
from app.models.company import Company
from app.models.enums import CompanyStatus, EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.incident import Incident


@pytest.fixture
def evidence_incident(db_session: Session) -> Incident:
    company = Company(
        id=uuid.uuid4(),
        name="Evidence Test Co",
        slug=f"evidence-{uuid.uuid4().hex[:6]}",
        industry="Retail",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Checkout Failure Cluster",
        summary="Elevated failures in checkout service",
        severity=SeverityLevel.MEDIUM,
        severity_reason="Initial medium severity",
        status=IncidentStatus.OPEN,
        affected_metrics=["checkout_failure_rate"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.flush()
    return incident


def test_calculate_relevance_score() -> None:
    now = datetime.now(UTC)
    # Anomaly with high severity close in time should score highest
    score_high = IncidentEvidenceService.calculate_relevance_score(
        source_type=EvidenceSourceType.ANOMALY,
        observed_at=now,
        incident_detected_at=now,
        severity=SeverityLevel.CRITICAL,
        is_direct_metric=True,
    )
    assert 0.90 <= score_high <= 0.99

    # Document 24 hours prior should score lower
    score_low = IncidentEvidenceService.calculate_relevance_score(
        source_type=EvidenceSourceType.DOCUMENT,
        observed_at=now - timedelta(days=1),
        incident_detected_at=now,
        severity=SeverityLevel.INFO,
        is_direct_metric=False,
    )
    assert 0.10 <= score_low < 0.70


def test_add_evidence_and_deduplication(db_session: Session, evidence_incident: Incident) -> None:
    now = datetime.now(UTC)
    dep_id = str(uuid.uuid4())

    ev1 = IncidentEvidenceService.add_evidence(
        db=db_session,
        incident_id=evidence_incident.id,
        source_type=EvidenceSourceType.DEPLOYMENT,
        source_id=dep_id,
        title="Deployment of checkout v1.2.0",
        summary="Service deployed",
        observed_at=now - timedelta(minutes=5),
        actor="operator_sam",
    )
    assert ev1.id is not None
    assert ev1.source_type == EvidenceSourceType.DEPLOYMENT
    assert ev1.source_id == dep_id
    assert ev1.relevance_score > 0.8

    # Adding exact same evidence again should return existing without creating a duplicate
    ev2 = IncidentEvidenceService.add_evidence(
        db=db_session,
        incident_id=evidence_incident.id,
        source_type=EvidenceSourceType.DEPLOYMENT,
        source_id=dep_id,
        title="Deployment duplicate",
        summary="Service deployed duplicate",
        observed_at=now - timedelta(minutes=5),
        actor="operator_sam",
    )
    assert ev1.id == ev2.id

    evidence_list = IncidentEvidenceService.list_evidence(
        db=db_session, incident_id=evidence_incident.id
    )
    assert len(evidence_list) == 1


def test_evidence_monotonic_severity_escalation(
    db_session: Session, evidence_incident: Incident
) -> None:
    assert evidence_incident.severity == SeverityLevel.MEDIUM

    # Attaching a critical evidence item escalates the parent incident severity to CRITICAL
    IncidentEvidenceService.add_evidence(
        db=db_session,
        incident_id=evidence_incident.id,
        source_type=EvidenceSourceType.SYSTEM_EVENT,
        source_id=str(uuid.uuid4()),
        title="Cascading Host Outage",
        summary="Complete failure of primary database cluster",
        observed_at=datetime.now(UTC),
        severity=SeverityLevel.CRITICAL,
    )

    db_session.refresh(evidence_incident)
    assert evidence_incident.severity == SeverityLevel.CRITICAL
    assert "Critical evidence attached" in (evidence_incident.severity_reason or "")
