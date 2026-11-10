"""Unit tests for Action Verification Service."""

import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.orm import Session

from app.actions.infrastructure import SimulatedInfrastructure
from app.actions.verification import VerificationService
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
    VerificationOutcome,
)
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.metrics import OperationalMetric
from app.models.recommendation import Recommendation


@pytest.fixture
def verification_test_data(db_session: Session):
    SimulatedInfrastructure.get_instance().reset()

    company = Company(
        id=uuid.uuid4(),
        name="VerifCorp",
        slug=f"verifcorp-{uuid.uuid4().hex[:6]}",
        industry="Technology",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Checkout Latency Incident",
        summary="High checkout failure rate",
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
        summary="Analysis complete",
        status=InvestigationStatus.COMPLETED,
    )
    db_session.add(investigation)
    db_session.flush()


    recommendation = Recommendation(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback checkout-service",
        description="Rollback to stable version",
        priority=TicketPriority.HIGH,
        risk_level=SeverityLevel.HIGH,
        expected_impact="Reduces error rate",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(recommendation)
    db_session.flush()

    now = datetime.now(UTC)
    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Rollback deployment",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="checkout-service",
        parameters={"service": "checkout-service", "target_version": "v4.8.1"},
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.EXECUTED,
        requested_by="operator_1",
        approved_by="admin_lead",
        executed_at=now - timedelta(minutes=2),
    )
    db_session.add(action)
    db_session.commit()

    return company, incident, recommendation, action


def test_verification_detects_recovery_success(db_session: Session, verification_test_data):
    """Verify healthy post-execution metrics produce VERIFIED_SUCCESS outcome."""
    company, incident, _, action = verification_test_data
    now = datetime.now(UTC)

    # Set simulated infrastructure version to match target version
    infra = SimulatedInfrastructure.get_instance()
    infra.services["checkout-service"]["active_deployment"] = "v4.8.1"

    # Add post-action recovered metrics
    db_session.add_all([
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="api_error_rate",
            value=0.85,  # <= 2.0%
            unit="percent",
            source="api-gateway",
            timestamp=now - timedelta(seconds=30),
        ),
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="api_latency_p95",
            value=175.0,  # <= 300ms
            unit="ms",
            source="api-gateway",
            timestamp=now - timedelta(seconds=30),
        ),
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="checkout_failure_rate",
            value=1.1,  # <= 3.0%
            unit="percent",
            source="api-gateway",
            timestamp=now - timedelta(seconds=30),
        ),
    ])
    db_session.commit()

    result = VerificationService.verify(db_session, action)

    assert result.outcome == VerificationOutcome.VERIFIED_SUCCESS
    assert result.signals_verified == 4
    assert result.signals_failed == 0
    assert action.status == ActionStatus.VERIFIED


def test_verification_detects_failure_when_still_degraded(db_session: Session, verification_test_data):
    """Verify persistently high error rate produces VERIFICATION_FAILED or PARTIAL outcome."""
    company, incident, _, action = verification_test_data
    now = datetime.now(UTC)

    # Mismatched deployment in simulated infra
    infra = SimulatedInfrastructure.get_instance()
    infra.services["checkout-service"]["active_deployment"] = "v4.8.2"

    # Post-action metric is still critically elevated
    db_session.add_all([
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="api_error_rate",
            value=25.0,  # 25% error rate
            unit="percent",
            source="api-gateway",
            timestamp=now - timedelta(seconds=10),
        ),
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="api_latency_p95",
            value=950.0,
            unit="ms",
            source="api-gateway",
            timestamp=now - timedelta(seconds=10),
        ),
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="checkout_failure_rate",
            value=45.0,
            unit="percent",
            source="api-gateway",
            timestamp=now - timedelta(seconds=10),
        ),
    ])
    db_session.commit()

    result = VerificationService.verify(db_session, action)

    assert result.outcome == VerificationOutcome.VERIFICATION_FAILED
    assert result.signals_failed == 4
    assert action.status == ActionStatus.VERIFICATION_FAILED
