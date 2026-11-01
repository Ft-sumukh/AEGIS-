"""Unit tests for incident lifecycle state machine, transitions, acknowledgement, and resolution."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.incidents.lifecycle import IncidentLifecycleManager
from app.incidents.models import InvalidLifecycleTransitionError
from app.models.company import Company
from app.models.enums import CompanyStatus, IncidentStatus, SeverityLevel
from app.models.incident import Incident


@pytest.fixture
def base_incident(db_session: Session) -> Incident:
    company = Company(
        id=uuid.uuid4(),
        name="Lifecycle Corp",
        slug=f"lifecycle-corp-{uuid.uuid4().hex[:6]}",
        industry="SaaS",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="API Gateway 502 Cascade",
        summary="Upstream services returning HTTP 502 Bad Gateway",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        category="API",
        affected_systems=["api-gateway"],
        affected_metrics=["error_rate_5xx"],
        detected_at=datetime.now(UTC),
        estimated_revenue_impact=Decimal("500.00"),
    )
    db_session.add(incident)
    db_session.flush()
    return incident


def test_acknowledgement(db_session: Session, base_incident: Incident) -> None:
    assert base_incident.acknowledged_at is None
    assert base_incident.acknowledged_by is None

    IncidentLifecycleManager.acknowledge(
        db=db_session,
        incident=base_incident,
        actor="oncall_bob",
        transition_to_investigating=True,
    )

    assert base_incident.acknowledged_at is not None
    assert base_incident.acknowledged_by == "oncall_bob"
    assert base_incident.status == IncidentStatus.INVESTIGATING
    assert base_incident.investigation_started_at is not None


def test_valid_lifecycle_progression(db_session: Session, base_incident: Incident) -> None:
    # 1. OPEN -> INVESTIGATING
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.INVESTIGATING,
        actor="alice_lead",
        reason="Triage started",
    )
    assert base_incident.status == IncidentStatus.INVESTIGATING
    assert base_incident.investigation_started_at is not None

    # 2. INVESTIGATING -> MITIGATED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.MITIGATED,
        actor="alice_lead",
        reason="Traffic shed and rate limiting enabled",
    )
    assert base_incident.status == IncidentStatus.MITIGATED
    assert base_incident.mitigated_at is not None

    # 3. MITIGATED -> RESOLVED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.RESOLVED,
        actor="alice_lead",
        resolution_summary="Connection pool exhausted due to idle socket leak. Rolled back build v2.1.0.",
    )
    assert base_incident.status == IncidentStatus.RESOLVED
    assert base_incident.resolved_at is not None
    assert base_incident.resolved_by == "alice_lead"
    assert "idle socket leak" in (base_incident.resolution_summary or "")

    # 4. RESOLVED -> CLOSED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.CLOSED,
        actor="charlie_manager",
        closed_by="charlie_manager",
    )
    assert base_incident.status == IncidentStatus.CLOSED
    assert base_incident.closed_at is not None
    assert base_incident.closed_by == "charlie_manager"


def test_invalid_resolution_without_summary(db_session: Session, base_incident: Incident) -> None:
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.INVESTIGATING,
        actor="alice_lead",
    )

    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        IncidentLifecycleManager.transition(
            db=db_session,
            incident=base_incident,
            new_status=IncidentStatus.RESOLVED,
            actor="alice_lead",
            resolution_summary="",  # Empty resolution summary must be rejected
        )
    assert "resolution summary is required" in str(exc_info.value)


def test_invalid_transition_from_closed_terminal(
    db_session: Session, base_incident: Incident
) -> None:
    # Transition to RESOLVED then CLOSED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.RESOLVED,
        actor="alice_lead",
        resolution_summary="Resolved via config update",
    )
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=base_incident,
        new_status=IncidentStatus.CLOSED,
        actor="alice_lead",
        closed_by="alice_lead",
    )
    assert base_incident.status == IncidentStatus.CLOSED

    # Attempt illegal reopen from terminal CLOSED state
    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        IncidentLifecycleManager.transition(
            db=db_session,
            incident=base_incident,
            new_status=IncidentStatus.OPEN,
            actor="alice_lead",
        )
    assert "not allowed" in str(exc_info.value)
