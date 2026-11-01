"""Unit tests for multi-source incident timeline aggregation, sorting, and privacy masking."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.incidents.timeline import IncidentTimelineService, mask_pii
from app.models.company import Company
from app.models.enums import (
    CompanyStatus,
    DeploymentStatus,
    IncidentStatus,
    SeverityLevel,
    TicketPriority,
    TicketStatus,
)
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident, IncidentNote
from app.models.support import SupportTicket


def test_mask_pii() -> None:
    raw = "Customer alice@example.com reported failure at 555-123-4567 during payment."
    masked = mask_pii(raw)
    assert "alice@example.com" not in masked
    assert "[REDACTED EMAIL]" in masked
    assert "555-123-4567" not in masked
    assert "[REDACTED PHONE]" in masked


def test_timeline_aggregation_and_ordering(db_session: Session) -> None:
    company = Company(
        id=uuid.uuid4(),
        name="Timeline Test Co",
        slug=f"timeline-{uuid.uuid4().hex[:6]}",
        industry="Retail",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)

    # 1. Deployment 30 mins prior
    dep = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="checkout-service",
        version="v3.4.1",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=t0 - timedelta(minutes=30),
        deployed_by="devops_dan",
    )
    db_session.add(dep)

    # 2. System event 10 mins prior
    sys_ev = SystemEvent(
        id=uuid.uuid4(),
        company_id=company.id,
        event_type="CONNECTION_POOL_EXHAUSTION",
        severity=SeverityLevel.HIGH,
        service="checkout-service",
        environment="production",
        message="Active connection count reached limit (100/100)",
        timestamp=t0 - timedelta(minutes=10),
    )
    db_session.add(sys_ev)

    # 3. Incident created at t0
    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Checkout Degradation Incident",
        summary="Checkout failure rate elevated",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.INVESTIGATING,
        category="CHECKOUT",
        affected_systems=["checkout-service"],
        affected_metrics=["checkout_failure_rate"],
        detected_at=t0,
        acknowledged_at=t0 + timedelta(minutes=5),
        acknowledged_by="oncall_eva",
        incident_metadata={"status_history": []},
    )
    db_session.add(incident)
    db_session.flush()

    # 4. Support ticket 15 mins later with PII
    tkt = SupportTicket(
        id=uuid.uuid4(),
        company_id=company.id,
        category="Checkout",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        summary="User testuser@acme.org called 212-555-0199 saying checkout is broken",
        created_at=t0 + timedelta(minutes=15),
    )
    db_session.add(tkt)

    # 5. Note 20 mins later
    note = IncidentNote(
        id=uuid.uuid4(),
        incident_id=incident.id,
        author="eva",
        text="Investigating DB pool settings. Email sent to team lead dave@ops.io",
        created_at=t0 + timedelta(minutes=20),
    )
    db_session.add(note)
    db_session.flush()

    # Build ascending timeline
    events_asc = IncidentTimelineService.build_timeline(
        db=db_session,
        incident=incident,
        ascending=True,
        include_adjacent_events=True,
    )

    assert len(events_asc) >= 5
    # Verify chronological order
    for i in range(len(events_asc) - 1):
        assert events_asc[i].timestamp <= events_asc[i + 1].timestamp

    # Verify PII masking on note and ticket
    note_event = next(e for e in events_asc if e.event_type == "NOTE_ADDED")
    assert "dave@ops.io" not in note_event.summary
    assert "[REDACTED EMAIL]" in note_event.summary

    ticket_event = next(e for e in events_asc if e.event_type == "SUPPORT_TICKET")
    assert "testuser@acme.org" not in ticket_event.summary
    assert "[REDACTED EMAIL]" in ticket_event.summary
    assert "212-555-0199" not in ticket_event.summary
    assert "[REDACTED PHONE]" in ticket_event.summary

    # Build descending timeline
    events_desc = IncidentTimelineService.build_timeline(
        db=db_session,
        incident=incident,
        ascending=False,
        include_adjacent_events=True,
    )
    assert events_desc[0].timestamp >= events_desc[-1].timestamp
