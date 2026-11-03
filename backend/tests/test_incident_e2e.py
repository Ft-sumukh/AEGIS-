"""End-to-End integration test covering Candidate -> Incident -> Lifecycle -> Evidence -> Timeline -> Audit."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.models import BusinessImpactEstimate, IncidentCandidate
from app.incidents.creation import IncidentCreationService
from app.incidents.evidence import IncidentEvidenceService
from app.incidents.impact import IncidentImpactService
from app.incidents.lifecycle import IncidentLifecycleManager
from app.incidents.timeline import IncidentTimelineService
from app.models.anomaly import Anomaly
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.enums import (
    AnomalyStatus,
    CompanyStatus,
    DeploymentStatus,
    DetectorType,
    EvidenceSourceType,
    IncidentStatus,
    SeverityLevel,
)
from app.models.events import Deployment, SystemEvent
from app.models.incident import IncidentNote


def test_full_incident_management_e2e_flow(db_session: Session) -> None:
    # 1. Company Setup
    company = Company(
        id=uuid.uuid4(),
        name="Global Commerce Systems",
        slug=f"global-commerce-{uuid.uuid4().hex[:6]}",
        industry="Retail",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    t0 = datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC)

    # 2. Prior deployment and technical events
    deployment = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="checkout-service",
        version="v5.0.0",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=t0 - timedelta(minutes=20),
        deployed_by="release_bot",
    )
    db_session.add(deployment)

    sys_ev = SystemEvent(
        id=uuid.uuid4(),
        company_id=company.id,
        event_type="DB_CONNECTION_FAILURE",
        severity=SeverityLevel.HIGH,
        service="checkout-service",
        environment="production",
        message="Database connection pool timeout",
        timestamp=t0 - timedelta(minutes=5),
    )
    db_session.add(sys_ev)

    # 3. Anomalies detected
    anom1 = Anomaly(
        id=uuid.uuid4(),
        company_id=company.id,
        metric_name="checkout_failure_rate",
        detector_type=DetectorType.Z_SCORE,
        severity=SeverityLevel.CRITICAL,
        status=AnomalyStatus.NEW,
        deviation=5.2,
        observed_value=48.2,
        expected_value=1.5,
        confidence=0.95,
        explanation="Checkout failure rate surged to 48.2%",
        detected_at=t0,
    )
    anom2 = Anomaly(
        id=uuid.uuid4(),
        company_id=company.id,
        metric_name="api_error_rate",
        detector_type=DetectorType.THRESHOLD,
        severity=SeverityLevel.HIGH,
        status=AnomalyStatus.NEW,
        deviation=4.0,
        observed_value=12.8,
        expected_value=0.5,
        confidence=0.95,
        explanation="API error rate jumped to 12.8%",
        detected_at=t0 + timedelta(minutes=1),
    )
    db_session.add_all([anom1, anom2])
    db_session.flush()

    # 4. Correlation produces IncidentCandidate
    candidate = IncidentCandidate(
        candidate_id=uuid.uuid4(),
        company_id=company.id,
        title="Critical Checkout & API Degradation",
        preliminary_summary="Correlation across checkout_failure_rate and api_error_rate",
        severity=SeverityLevel.CRITICAL,
        correlation_score=0.96,
        first_detected_at=t0,
        last_detected_at=t0 + timedelta(minutes=2),
        affected_metrics=["checkout_failure_rate", "api_error_rate"],
        anomaly_ids=[anom1.id, anom2.id],
        impact=BusinessImpactEstimate(
            estimated_revenue_impact=Decimal("15000.00"),
            estimated_orders_affected=180,
            estimated_users_affected=450,
            additional_support_tickets=25,
            additional_complaints=10,
        ),
    )

    # 5. Transform Candidate -> Incident
    incident, is_new = IncidentCreationService.create_from_candidate(
        db=db_session,
        candidate=candidate,
        actor="system",
    )
    assert is_new is True
    assert incident.status == IncidentStatus.OPEN
    assert incident.severity == SeverityLevel.CRITICAL
    assert incident.category == "CHECKOUT"
    assert len(incident.anomalies) == 2
    assert len(incident.evidence) >= 2  # Anomalies + deployment automatically correlated

    # 6. Operator Acknowledgement
    IncidentLifecycleManager.acknowledge(
        db=db_session,
        incident=incident,
        actor="sre_alice",
        transition_to_investigating=True,
    )
    assert incident.status == IncidentStatus.INVESTIGATING
    assert incident.acknowledged_by == "sre_alice"
    assert incident.investigation_started_at is not None

    # 7. Add Manual Operator Note
    note = IncidentNote(
        id=uuid.uuid4(),
        incident_id=incident.id,
        author="sre_alice",
        text="Correlating DB pool exhaustion with v5.0.0 deployment.",
        created_at=t0 + timedelta(minutes=10),
    )
    db_session.add(note)
    db_session.flush()

    # 8. Add Additional Evidence
    IncidentEvidenceService.add_evidence(
        db=db_session,
        incident_id=incident.id,
        source_type=EvidenceSourceType.SYSTEM_EVENT,
        source_id=str(sys_ev.id),
        title=f"Event {sys_ev.event_type}",
        summary=sys_ev.message,
        observed_at=sys_ev.timestamp,
        severity=sys_ev.severity,
        actor="sre_alice",
    )

    # 9. Update Business Impact
    impact_service = IncidentImpactService()
    delta = impact_service.update_incident_impact(
        db=db_session,
        incident=incident,
        new_revenue=18500.00,
        new_orders=210,
        actor="sre_alice",
    )
    assert delta.revenue_delta == 3500.00
    assert float(incident.estimated_revenue_impact) == 18500.00

    # 10. Lifecycle Transition: INVESTIGATING -> MITIGATED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=incident,
        new_status=IncidentStatus.MITIGATED,
        actor="sre_alice",
        reason="Rolled back checkout-service to v4.9.8",
    )
    assert incident.status == IncidentStatus.MITIGATED
    assert incident.mitigated_at is not None

    # 11. Lifecycle Transition: MITIGATED -> RESOLVED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=incident,
        new_status=IncidentStatus.RESOLVED,
        actor="sre_alice",
        resolution_summary="Rollback restored DB connection pool headroom. Order success rates returned to baseline.",
    )
    assert incident.status == IncidentStatus.RESOLVED
    assert incident.resolved_at is not None

    # 12. Lifecycle Transition: RESOLVED -> CLOSED
    IncidentLifecycleManager.transition(
        db=db_session,
        incident=incident,
        new_status=IncidentStatus.CLOSED,
        actor="incident_commander",
        closed_by="incident_commander",
    )
    assert incident.status == IncidentStatus.CLOSED
    assert incident.closed_at is not None

    # 13. Timeline Generation
    timeline = IncidentTimelineService.build_timeline(
        db=db_session,
        incident=incident,
        ascending=True,
    )
    assert len(timeline) >= 6
    event_types = [e.event_type for e in timeline]
    assert "INCIDENT_CREATED" in event_types
    assert "INCIDENT_ACKNOWLEDGED" in event_types
    assert "STATUS_CHANGED" in event_types
    assert "EVIDENCE_ADDED" in event_types
    assert "NOTE_ADDED" in event_types

    # 14. Audit Verification
    audits = list(
        db_session.scalars(
            select(AuditLog)
            .where(AuditLog.resource_id == str(incident.id))
            .order_by(AuditLog.timestamp.asc())
        ).all()
    )
    actions = [a.action for a in audits]
    assert "INCIDENT_CREATED" in actions
    assert "INCIDENT_ACKNOWLEDGED" in actions
    assert "INCIDENT_STATUS_CHANGED" in actions
    assert "INCIDENT_IMPACT_UPDATED" in actions
