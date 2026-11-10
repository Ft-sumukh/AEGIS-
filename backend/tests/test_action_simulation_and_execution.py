"""Unit tests for Action simulated infrastructure and execution."""

import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy.orm import Session


from app.actions.infrastructure import (
    ActionPreconditionFailedError,
    SimulatedExecutor,
    SimulatedInfrastructure,
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


@pytest.fixture
def base_test_data(db_session: Session):
    """Seed minimal incident and recommendation for execution tests."""
    SimulatedInfrastructure.get_instance().reset()

    company = Company(
        id=uuid.uuid4(),
        name="SimCorp",
        slug=f"simcorp-{uuid.uuid4().hex[:6]}",
        industry="Technology",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Simulated Checkout Error Outage",
        summary="Testing action simulation engine",
        severity=SeverityLevel.HIGH,
        category="APPLICATION",
        affected_systems=["checkout-service"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.flush()

    investigation = Investigation(
        id=uuid.uuid4(),
        incident_id=incident.id,
        summary="Diagnostics completed",
        status=InvestigationStatus.COMPLETED,
    )
    db_session.add(investigation)
    db_session.flush()


    recommendation = Recommendation(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback checkout-service to v4.8.1",
        description="Revert bad deployment to restore checkout flow",
        priority=TicketPriority.HIGH,
        risk_level=SeverityLevel.HIGH,
        expected_impact="Resolves elevated 500 error rates",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(recommendation)
    db_session.commit()

    return company, incident, recommendation


def test_dry_run_does_not_mutate_state(db_session: Session, base_test_data):
    """Verify dry_run executes preconditions without modifying simulated state or database."""
    _, incident, recommendation = base_test_data

    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Rollback deployment",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="checkout-service",
        parameters={"service": "checkout-service", "target_version": "v4.8.1"},
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.APPROVED,
        requested_by="operator_1",
        approved_by="admin_lead",
    )
    db_session.add(action)
    db_session.commit()

    result = SimulatedExecutor.execute(db_session, action, dry_run=True)

    assert result.success is True
    assert result.dry_run is True
    assert "Dry-run simulation passed" in result.message

    infra = SimulatedInfrastructure.get_instance()
    # State should remain untouched
    assert infra.get_service_state("checkout-service")["active_deployment"] == "v4.8.2"


def test_rollback_execution_mutates_state_and_emits_event(db_session: Session, base_test_data):
    """Verify executing rollback mutates simulated infra and persists system event."""
    _, incident, recommendation = base_test_data

    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Rollback deployment",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="checkout-service",
        parameters={"service": "checkout-service", "target_version": "v4.8.1"},
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.APPROVED,
        requested_by="operator_1",
        approved_by="admin_lead",
    )
    db_session.add(action)
    db_session.commit()

    result = SimulatedExecutor.execute(db_session, action, dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert len(result.emitted_events) > 0

    infra = SimulatedInfrastructure.get_instance()
    assert infra.get_service_state("checkout-service")["active_deployment"] == "v4.8.1"
    assert infra.get_service_state("checkout-service")["health_state"] == "HEALTHY"


def test_scale_service_execution(db_session: Session, base_test_data):
    """Verify executing scale action updates replica count in simulated infra."""
    _, incident, recommendation = base_test_data

    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Scale payment-gateway",
        action_type=ActionType.SCALE_SERVICE,
        target_service="payment-gateway",
        parameters={"service": "payment-gateway", "target_capacity": 6},
        risk_level=SeverityLevel.MEDIUM,
        status=ActionStatus.APPROVED,
        requested_by="operator_1",
        approved_by="admin_lead",
    )
    db_session.add(action)
    db_session.commit()

    result = SimulatedExecutor.execute(db_session, action, dry_run=False)

    assert result.success is True
    assert result.dry_run is False

    infra = SimulatedInfrastructure.get_instance()
    assert infra.get_service_state("payment-gateway")["desired_capacity"] == 6


def test_feature_flag_execution(db_session: Session, base_test_data):
    """Verify toggling feature flag updates simulated infra."""
    _, incident, recommendation = base_test_data

    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Disable checkout v2 optimization",
        action_type=ActionType.DISABLE_FEATURE_FLAG,
        target_service="checkout-service",
        parameters={"flag_name": "checkout_v2_optimization", "enabled": False},
        risk_level=SeverityLevel.MEDIUM,
        status=ActionStatus.APPROVED,
        requested_by="operator_1",
        approved_by="admin_lead",
    )
    db_session.add(action)
    db_session.commit()

    result = SimulatedExecutor.execute(db_session, action, dry_run=False)

    assert result.success is True
    assert result.dry_run is False

    infra = SimulatedInfrastructure.get_instance()
    assert infra.feature_flags["checkout_v2_optimization"] is False
