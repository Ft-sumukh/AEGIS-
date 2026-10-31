"""Unit tests for deterministic incident fingerprinting and deduplication."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.models import IncidentCandidate
from app.incidents.deduplication import IncidentDeduplicator
from app.models.company import Company
from app.models.enums import CompanyStatus, IncidentStatus, SeverityLevel
from app.models.incident import Incident


def test_fingerprint_determinism_and_temporal_window() -> None:
    comp_id = uuid.uuid4()
    t1 = datetime(2026, 8, 10, 14, 15, 0, tzinfo=UTC)
    t2 = datetime(
        2026, 8, 10, 15, 45, 0, tzinfo=UTC
    )  # Same 4-hour bucket (hour 14 and 15 both hour // 4 == 3)
    t3 = datetime(2026, 8, 10, 18, 0, 0, tzinfo=UTC)  # Different bucket (hour 18 // 4 == 4)

    cand1 = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=comp_id,
        title="Cluster A",
        preliminary_summary="Summary",
        severity=SeverityLevel.HIGH,
        correlation_score=0.8,
        first_detected_at=t1,
        last_detected_at=t1,
        affected_metrics=["checkout_failure_rate", "api_error_rate"],
    )

    cand2 = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=comp_id,
        title="Cluster B",
        preliminary_summary="Summary",
        severity=SeverityLevel.HIGH,
        correlation_score=0.8,
        first_detected_at=t2,
        last_detected_at=t2,
        affected_metrics=["api_error_rate", "checkout_failure_rate"],  # Reversed order
    )

    cand3 = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=comp_id,
        title="Cluster C",
        preliminary_summary="Summary",
        severity=SeverityLevel.HIGH,
        correlation_score=0.8,
        first_detected_at=t3,
        last_detected_at=t3,
        affected_metrics=["checkout_failure_rate", "api_error_rate"],
    )

    fp1 = IncidentDeduplicator.generate_candidate_fingerprint(cand1)
    fp2 = IncidentDeduplicator.generate_candidate_fingerprint(cand2)
    fp3 = IncidentDeduplicator.generate_candidate_fingerprint(cand3)

    assert fp1 == fp2  # Same bucket & metric set regardless of ordering
    assert fp1 != fp3  # Different temporal bucket produces different fingerprint


def test_deduplication_evaluate(db_session: Session) -> None:
    company = Company(
        id=uuid.uuid4(),
        name="Dedup Test Co",
        slug=f"dedup-{uuid.uuid4().hex[:6]}",
        industry="Retail",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    fp = "sample-deterministic-fingerprint-abc"
    res1 = IncidentDeduplicator.evaluate(db_session, company.id, fp)
    assert res1.is_duplicate is False

    inc = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Active Incident",
        summary="Active",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        fingerprint=fp,
        detected_at=datetime.now(UTC),
    )
    db_session.add(inc)
    db_session.flush()

    res2 = IncidentDeduplicator.evaluate(db_session, company.id, fp)
    assert res2.is_duplicate is True
    assert res2.existing_incident_id == inc.id

    # Once closed, fingerprint no longer blocks a new incident
    inc.status = IncidentStatus.CLOSED
    db_session.flush()

    res3 = IncidentDeduplicator.evaluate(db_session, company.id, fp)
    assert res3.is_duplicate is False
