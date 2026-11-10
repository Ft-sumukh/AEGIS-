"""Unit tests for Action idempotency and concurrent execution conflict prevention."""

import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy.orm import Session

from app.actions.policy import (
    ActionPolicyEngine,
    ConcurrentActionConflictError,
)
from app.models.action import Action
from app.models.company import Company
from app.models.enums import (
    ActionStatus,
    ActionType,
    CompanyStatus,
    InvestigationStatus,
    RecommendationStatus,
    SeverityLevel,
    TicketPriority,
)
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.recommendation import Recommendation


def test_concurrent_action_on_same_service_is_blocked(db_session: Session):
    """Verify check_target_concurrency raises ConcurrentActionConflictError if an action is executing."""
    company = Company(
        id=uuid.uuid4(),
        name="ConcurrencyCorp",
        slug=f"cc-{uuid.uuid4().hex[:6]}",
        industry="Technology",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Concurrent Incident",
        summary="Testing concurrency locks",
        severity=SeverityLevel.HIGH,
        category="APPLICATION",
        affected_systems=["order-service"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.flush()

    investigation = Investigation(
        id=uuid.uuid4(),
        incident_id=incident.id,
        summary="Investigating latency",
        status=InvestigationStatus.COMPLETED,
    )
    db_session.add(investigation)
    db_session.flush()


    rec = Recommendation(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback",
        description="Rollback deployment",
        priority=TicketPriority.HIGH,
        risk_level=SeverityLevel.HIGH,
        expected_impact="Restore availability",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(rec)
    db_session.flush()

    # Active running action on order-service
    active_action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=rec.id,
        title="Rollback 1",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="order-service",
        parameters={"service": "order-service", "target_version": "v1.0"},
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.EXECUTING,
        requested_by="operator_1",
    )
    db_session.add(active_action)
    db_session.commit()

    # Attempt to execute another action on the same service
    new_action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=rec.id,
        title="Restart 2",
        action_type=ActionType.RESTART_SERVICE,
        target_service="order-service",
        parameters={"service": "order-service", "grace_period_seconds": 10},
        risk_level=SeverityLevel.MEDIUM,
        status=ActionStatus.APPROVED,
        requested_by="operator_2",
    )
    db_session.add(new_action)
    db_session.commit()

    with pytest.raises(ConcurrentActionConflictError):
        ActionPolicyEngine.check_target_concurrency(
            db_session,
            target_service=new_action.target_service,
            exclude_action_id=new_action.id,
        )

