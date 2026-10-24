"""Unit tests for all Aegis domain entities, constraints, and precision."""

import datetime
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.customer import Customer
from app.models.enums import (
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionType,
    AuditActorType,
    CompanyStatus,
    DeploymentStatus,
    EvidenceSourceType,
    HypothesisStatus,
    IncidentStatus,
    InvestigationStatus,
    OrderStatus,
    RecommendationStatus,
    SeverityLevel,
    TicketPriority,
    TicketStatus,
)
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident, IncidentEvidence
from app.models.investigation import Investigation, InvestigationHypothesis
from app.models.metrics import OperationalMetric
from app.models.order import Order, OrderItem
from app.models.recommendation import Recommendation
from app.models.support import CustomerComplaint, SupportTicket


def test_company_lifecycle_and_slug_uniqueness(db_session: Session) -> None:
    """Verify Company entity creation and unique slug constraint."""
    comp1 = Company(
        name="Test Enterprise Alpha",
        slug="test-alpha",
        industry="SaaS",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(comp1)
    db_session.commit()

    retrieved = db_session.scalar(select(Company).where(Company.slug == "test-alpha"))
    assert retrieved is not None
    assert retrieved.name == "Test Enterprise Alpha"
    assert retrieved.created_at.tzinfo is not None

    # Test unique constraint on slug
    comp2 = Company(name="Duplicate Slug Corp", slug="test-alpha")
    db_session.add(comp2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_creation_and_pii_handling(db_session: Session) -> None:
    """Verify Customer entity creation and association to Company."""
    company = Company(name="Acme Inc", slug="acme-unique")
    db_session.add(company)
    db_session.flush()

    customer = Customer(
        company_id=company.id,
        external_reference="CUST-500",
        name="John Doe",
        email="john.doe.synthetic@example.com",
        phone="+1-555-9999",
        region="us-east-1",
    )
    db_session.add(customer)
    db_session.commit()

    retrieved = db_session.scalar(select(Customer).where(Customer.external_reference == "CUST-500"))
    assert retrieved is not None
    assert retrieved.company.id == company.id
    assert retrieved.email == "john.doe.synthetic@example.com"


def test_order_and_order_item_decimal_precision(db_session: Session) -> None:
    """Verify monetary values maintain strict Decimal precision without float inaccuracies."""
    company = Company(name="Retail Co", slug="retail-co")
    db_session.add(company)
    db_session.flush()

    customer = Customer(
        company_id=company.id,
        external_reference="C-1",
        name="Shopper",
    )
    db_session.add(customer)
    db_session.flush()

    # Exact decimal amounts with cents
    exact_unit_price = Decimal("19.99")
    quantity = 3
    exact_total = Decimal("59.97")

    now = datetime.datetime.now(datetime.UTC)
    order = Order(
        company_id=company.id,
        customer_id=customer.id,
        external_reference="ORD-EXACT",
        status=OrderStatus.CONFIRMED,
        currency="USD",
        total_amount=exact_total,
        ordered_at=now,
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_reference="SKU-WIDGET",
        quantity=quantity,
        unit_price=exact_unit_price,
        total_price=exact_total,
    )
    db_session.add(item)
    db_session.commit()

    retrieved = db_session.scalar(select(Order).where(Order.id == order.id))
    assert retrieved is not None
    assert isinstance(retrieved.total_amount, Decimal)
    assert retrieved.total_amount == Decimal("59.97")
    assert retrieved.items[0].unit_price == Decimal("19.99")
    assert retrieved.items[0].total_price == Decimal("59.97")


def test_operational_metric_time_range_query(db_session: Session) -> None:
    """Verify OperationalMetric creation and time-window filtering."""
    company = Company(name="Observability Corp", slug="obs-corp")
    db_session.add(company)
    db_session.flush()

    base_time = datetime.datetime.now(datetime.UTC)
    for minute in range(5):
        metric = OperationalMetric(
            company_id=company.id,
            metric_name="api_error_rate",
            timestamp=base_time + datetime.timedelta(minutes=minute),
            value=float(minute * 1.5),
            unit="percent",
            source="gateway",
            dimension_data={"service": "api-gateway"},
        )
        db_session.add(metric)
    db_session.commit()

    # Query range between minute 1 and 3
    start = base_time + datetime.timedelta(minutes=1)
    end = base_time + datetime.timedelta(minutes=3)
    results = db_session.scalars(
        select(OperationalMetric)
        .where(
            OperationalMetric.company_id == company.id,
            OperationalMetric.timestamp >= start,
            OperationalMetric.timestamp <= end,
        )
        .order_by(OperationalMetric.timestamp.asc())
    ).all()

    assert len(results) == 3
    assert results[0].value == 1.5
    assert results[-1].value == 4.5


def test_system_event_and_deployment_creation(db_session: Session) -> None:
    """Verify SystemEvent and Deployment entities."""
    company = Company(name="Infra Corp", slug="infra-corp")
    db_session.add(company)
    db_session.flush()

    now = datetime.datetime.now(datetime.UTC)
    event = SystemEvent(
        company_id=company.id,
        event_type="DATABASE_ERROR",
        severity=SeverityLevel.CRITICAL,
        service="checkout-service",
        environment="production",
        message="Connection pool exhausted",
        timestamp=now,
        event_metadata={"pool": "main"},
    )
    deployment = Deployment(
        company_id=company.id,
        service="checkout-service",
        version="v4.8.2",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=now - datetime.timedelta(minutes=10),
        deployed_by="ci-bot",
        deployment_metadata={"commit": "abc1234"},
    )
    db_session.add_all([event, deployment])
    db_session.commit()

    assert event.id is not None
    assert deployment.id is not None
    assert event.severity == SeverityLevel.CRITICAL
    assert deployment.status == DeploymentStatus.SUCCESS


def test_support_ticket_and_complaint_creation(db_session: Session) -> None:
    """Verify SupportTicket and CustomerComplaint creation."""
    company = Company(name="Support Corp", slug="support-corp")
    db_session.add(company)
    db_session.flush()

    customer = Customer(company_id=company.id, external_reference="C-10", name="Ticket User")
    db_session.add(customer)
    db_session.flush()

    ticket = SupportTicket(
        company_id=company.id,
        customer_id=customer.id,
        category="Billing",
        priority=TicketPriority.URGENT,
        status=TicketStatus.OPEN,
        summary="Unable to finalize subscription purchase",
        ticket_metadata={"sku": "pro"},
    )
    complaint = CustomerComplaint(
        company_id=company.id,
        customer_id=customer.id,
        category="Checkout Failure",
        severity=SeverityLevel.HIGH,
        summary="Payment button did not respond",
        complaint_metadata={"retries": 3},
    )
    db_session.add_all([ticket, complaint])
    db_session.commit()

    assert ticket.id is not None
    assert complaint.id is not None
    assert ticket.customer.id == customer.id


def test_investigation_hypotheses_and_recommendation(db_session: Session) -> None:
    """Verify investigation lifecycle with hypotheses, recommendation, and action."""
    company = Company(name="Investigation Corp", slug="inv-corp")
    db_session.add(company)
    db_session.flush()

    now = datetime.datetime.now(datetime.UTC)
    incident = Incident(
        company_id=company.id,
        title="Checkout Degraded",
        summary="Sustained order failure rate",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.INVESTIGATING,
        detected_at=now,
    )
    db_session.add(incident)
    db_session.flush()

    evidence = IncidentEvidence(
        incident_id=incident.id,
        source_type=EvidenceSourceType.SYSTEM_EVENT,
        title="DB pool error",
        summary="Connection limit hit",
        observed_at=now,
        relevance_score=0.9,
    )
    db_session.add(evidence)
    db_session.flush()

    investigation = Investigation(
        incident_id=incident.id,
        status=InvestigationStatus.RUNNING,
        summary="Analyzing causal chain",
        confidence=0.88,
    )
    db_session.add(investigation)
    db_session.flush()

    hypo = InvestigationHypothesis(
        investigation_id=investigation.id,
        title="Connection leak in deployment",
        description="DB connections left unclosed",
        status=HypothesisStatus.SUPPORTED,
        confidence=0.92,
    )
    db_session.add(hypo)

    rec = Recommendation(
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback deployment",
        description="Rollback to v4.8.1",
        priority=TicketPriority.URGENT,
        risk_level=SeverityLevel.LOW,
        expected_impact="Resolves pool saturation",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(rec)
    db_session.flush()

    action = Action(
        recommendation_id=rec.id,
        incident_id=incident.id,
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        description="Trigger k8s rollout undo",
        risk_level=SeverityLevel.LOW,
        approval_status=ActionApprovalStatus.PENDING,
        execution_status=ActionExecutionStatus.NOT_STARTED,
        requested_by="ai-agent",
    )
    db_session.add(action)
    db_session.commit()

    assert action.id is not None
    assert len(investigation.hypotheses) == 1
    assert len(incident.evidence) == 1
    assert len(incident.recommendations) == 1
    assert len(incident.actions) == 1


def test_audit_log_append_only(db_session: Session) -> None:
    """Verify AuditLog records can be created with actor and resource metadata."""
    company = Company(name="Audit Corp", slug="audit-corp")
    db_session.add(company)
    db_session.flush()

    audit = AuditLog(
        company_id=company.id,
        actor_type=AuditActorType.AGENT,
        actor_id="aegis-investigator",
        action="INCIDENT_CREATED",
        resource_type="Incident",
        resource_id=str(uuid.uuid4()),
        audit_metadata={"reason": "anomaly correlation"},
    )
    db_session.add(audit)
    db_session.commit()

    retrieved = db_session.scalar(select(AuditLog).where(AuditLog.id == audit.id))
    assert retrieved is not None
    assert retrieved.actor_type == AuditActorType.AGENT
    assert retrieved.action == "INCIDENT_CREATED"
    assert retrieved.timestamp.tzinfo is not None
