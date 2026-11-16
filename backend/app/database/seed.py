"""Seed database with realistic, coherent operational incident narrative."""

import datetime
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger, setup_logging
from app.database.session import get_session_factory
from app.models.action import Action
from app.models.anomaly import Anomaly
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.customer import Customer
from app.models.enums import (
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionType,
    AnomalyStatus,
    AuditActorType,
    CompanyStatus,
    DeploymentStatus,
    DetectorType,
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

logger = get_logger("aegis.seed")


def seed_database(db: Session) -> dict[str, Any]:
    """Execute coherent narrative database seeding.

    Narrative Sequence:
    1. Acme Cloud Commerce (Fictional Company)
    2. 3 Customers (Alice, Bob, Charlie)
    3. Normal baseline metrics & healthy orders
    4. 14:00 UTC: Deployment of checkout-service v4.8.2
    5. 14:05 UTC: DATABASE_ERROR connection exhaustion events
    6. 14:06 UTC: api_error_rate spike
    7. 14:07 UTC: checkout_failure_rate spike
    8. 14:08 UTC: Orders start failing
    9. 14:10 UTC: Customer complaints & urgent support tickets filed
    10. 14:12 UTC: Anomalies detected on checkout_failure_rate & api_error_rate
    11. 14:15 UTC: Incident created linking anomalies and evidence
    12. 14:16 UTC: Investigation started with 2 hypotheses
    13. 14:18 UTC: Recommendation to rollback deployment generated
    14. 14:20 UTC: Rollback action proposed awaiting human approval
    15. Append-only audit logs recorded throughout
    """
    logger.info("Starting Aegis database seeding...")

    # Base reference timestamp (yesterday 14:00 UTC)
    base_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    t_0 = base_time.replace(hour=14, minute=0, second=0, microsecond=0)

    # 1. Company
    company = Company(
        id=uuid.uuid4(),
        name="Acme Cloud Commerce",
        slug="acme-corp",
        industry="E-Commerce & Retail",
        status=CompanyStatus.ACTIVE,
        created_at=t_0 - datetime.timedelta(days=30),
    )
    db.add(company)
    db.flush()

    # 2. Customers
    cust_alice = Customer(
        id=uuid.uuid4(),
        company_id=company.id,
        external_reference="CUST-1001",
        name="Alice Walker",
        email="alice.synthetic@acme-demo.internal",
        phone="+1-555-0101",
        region="us-east-1",
        created_at=t_0 - datetime.timedelta(days=20),
    )
    cust_bob = Customer(
        id=uuid.uuid4(),
        company_id=company.id,
        external_reference="CUST-1002",
        name="Bob Miller",
        email="bob.synthetic@acme-demo.internal",
        phone="+1-555-0102",
        region="us-west-2",
        created_at=t_0 - datetime.timedelta(days=15),
    )
    cust_charlie = Customer(
        id=uuid.uuid4(),
        company_id=company.id,
        external_reference="CUST-1003",
        name="Charlie Davis",
        email="charlie.synthetic@acme-demo.internal",
        phone="+1-555-0103",
        region="eu-central-1",
        created_at=t_0 - datetime.timedelta(days=10),
    )
    db.add_all([cust_alice, cust_bob, cust_charlie])
    db.flush()

    # 3. Baseline Healthy Orders
    healthy_order = Order(
        id=uuid.uuid4(),
        company_id=company.id,
        customer_id=cust_alice.id,
        external_reference="ORD-9010",
        status=OrderStatus.COMPLETED,
        currency="USD",
        total_amount=Decimal("149.99"),
        ordered_at=t_0 - datetime.timedelta(minutes=30),
    )
    db.add(healthy_order)
    db.flush()

    item1 = OrderItem(
        id=uuid.uuid4(),
        order_id=healthy_order.id,
        product_reference="PROD-HEADPHONES",
        quantity=1,
        unit_price=Decimal("149.99"),
        total_price=Decimal("149.99"),
    )
    db.add(item1)

    # 4. Deployment Event at 14:00
    deployment = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="checkout-service",
        version="v4.8.2",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=t_0,
        deployed_by="ci-deploy-bot@acme-demo.internal",
        deployment_metadata={
            "git_commit": "a1c8f90",
            "branch": "main",
            "change_summary": "Optimize db connection handling in checkout flow",
        },
    )
    db.add(deployment)
    db.flush()

    # 5. System Events: DB connection error at 14:05
    event1 = SystemEvent(
        id=uuid.uuid4(),
        company_id=company.id,
        event_type="DATABASE_ERROR",
        severity=SeverityLevel.CRITICAL,
        service="checkout-service",
        environment="production",
        message="Database connection pool exhausted: 100/100 active connections acquired with 42 waiting requests",
        timestamp=t_0 + datetime.timedelta(minutes=5),
        event_metadata={"pool_size": 100, "waiting_threads": 42, "error_code": "POOL_EXHAUSTED"},
    )
    event2 = SystemEvent(
        id=uuid.uuid4(),
        company_id=company.id,
        event_type="CHECKOUT_FAILURE",
        severity=SeverityLevel.ERROR,
        service="checkout-service",
        environment="production",
        message="Payment confirmation request timed out after 30000ms",
        timestamp=t_0 + datetime.timedelta(minutes=7),
        event_metadata={"timeout_ms": 30000, "gateway": "acme-pay"},
    )
    db.add_all([event1, event2])
    db.flush()

    # 6. Operational Metrics: Baseline to Anomaly Progression
    metrics_data = [
        # Normal baseline before deployment
        ("api_error_rate", t_0 - datetime.timedelta(minutes=15), 0.12, "percent", "gateway"),
        (
            "checkout_failure_rate",
            t_0 - datetime.timedelta(minutes=15),
            0.02,
            "percent",
            "checkout",
        ),
        ("revenue", t_0 - datetime.timedelta(minutes=15), 4500.00, "usd_per_min", "billing"),
        ("active_users", t_0 - datetime.timedelta(minutes=15), 1840.0, "users", "analytics"),
        # Post-deployment degradation
        ("api_error_rate", t_0 + datetime.timedelta(minutes=6), 18.5, "percent", "gateway"),
        ("checkout_failure_rate", t_0 + datetime.timedelta(minutes=7), 42.8, "percent", "checkout"),
        ("revenue", t_0 + datetime.timedelta(minutes=10), 420.00, "usd_per_min", "billing"),
        ("active_users", t_0 + datetime.timedelta(minutes=10), 1610.0, "users", "analytics"),
    ]

    metric_entities: list[OperationalMetric] = []
    for m_name, m_ts, m_val, m_unit, m_src in metrics_data:
        m = OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name=m_name,
            timestamp=m_ts,
            value=m_val,
            unit=m_unit,
            source=m_src,
            dimension_data={"service": "checkout-service", "region": "us-east-1"},
        )
        metric_entities.append(m)
        db.add(m)
    db.flush()

    # 7. Failed Orders during incident window
    failed_order_1 = Order(
        id=uuid.uuid4(),
        company_id=company.id,
        customer_id=cust_bob.id,
        external_reference="ORD-9021",
        status=OrderStatus.FAILED,
        currency="USD",
        total_amount=Decimal("389.50"),
        ordered_at=t_0 + datetime.timedelta(minutes=8),
    )
    failed_order_2 = Order(
        id=uuid.uuid4(),
        company_id=company.id,
        customer_id=cust_charlie.id,
        external_reference="ORD-9022",
        status=OrderStatus.FAILED,
        currency="USD",
        total_amount=Decimal("94.20"),
        ordered_at=t_0 + datetime.timedelta(minutes=9),
    )
    db.add_all([failed_order_1, failed_order_2])
    db.flush()

    # 8. Customer Complaints & Urgent Support Tickets
    complaint1 = CustomerComplaint(
        id=uuid.uuid4(),
        company_id=company.id,
        customer_id=cust_bob.id,
        category="Checkout Error",
        severity=SeverityLevel.HIGH,
        summary="Payment failed at final checkout button after entering card details. Cart was emptied.",
        created_at=t_0 + datetime.timedelta(minutes=10),
        complaint_metadata={"browser": "Chrome 122", "order_ref": "ORD-9021"},
    )
    ticket1 = SupportTicket(
        id=uuid.uuid4(),
        company_id=company.id,
        customer_id=cust_charlie.id,
        category="Billing/Checkout",
        priority=TicketPriority.URGENT,
        status=TicketStatus.OPEN,
        summary="Customer reports 500 internal server error during order finalization.",
        created_at=t_0 + datetime.timedelta(minutes=11),
        ticket_metadata={"impacted_sku": "PROD-MONITOR", "channel": "web"},
    )
    db.add_all([complaint1, ticket1])
    db.flush()

    # 9. Anomalies Detected
    checkout_metric = next(
        m for m in metric_entities if m.metric_name == "checkout_failure_rate" and m.value > 1.0
    )
    api_metric = next(
        m for m in metric_entities if m.metric_name == "api_error_rate" and m.value > 1.0
    )

    anomaly_checkout = Anomaly(
        id=uuid.uuid4(),
        company_id=company.id,
        metric_id=checkout_metric.id,
        metric_name="checkout_failure_rate",
        detected_at=t_0 + datetime.timedelta(minutes=12),
        observed_value=42.8,
        expected_value=0.02,
        deviation=42.78,
        detector_type=DetectorType.Z_SCORE,
        severity=SeverityLevel.CRITICAL,
        confidence=0.98,
        explanation="Checkout failure rate surged from baseline 0.02% to 42.8% (+2140x normal baseline deviation).",
        status=AnomalyStatus.CORRELATED,
        anomaly_metadata={"z_score": 8.4, "baseline_window": "24h"},
    )
    anomaly_api = Anomaly(
        id=uuid.uuid4(),
        company_id=company.id,
        metric_id=api_metric.id,
        metric_name="api_error_rate",
        detected_at=t_0 + datetime.timedelta(minutes=12),
        observed_value=18.5,
        expected_value=0.12,
        deviation=18.38,
        detector_type=DetectorType.THRESHOLD,
        severity=SeverityLevel.HIGH,
        confidence=0.95,
        explanation="API gateway 5xx error rate exceeded 5.0% threshold (observed 18.5%).",
        status=AnomalyStatus.CORRELATED,
        anomaly_metadata={"threshold": 5.0},
    )
    db.add_all([anomaly_checkout, anomaly_api])
    db.flush()

    # 10. Incident Created
    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Critical Checkout Service Outage & Elevated API Failure Rate",
        summary="Widespread failure in checkout-service leading to 42.8% order rejection rate and database pool exhaustion following deployment v4.8.2.",
        severity=SeverityLevel.CRITICAL,
        severity_reason="CRITICAL because critical anomaly threshold breached on checkout_failure_rate; estimated revenue impact ($12,500.00) exceeded threshold.",
        status=IncidentStatus.INVESTIGATING,
        category="CHECKOUT",
        tags=["checkout", "database", "seed-narrative"],
        affected_systems=["checkout-service", "postgres-cluster"],
        affected_metrics=["checkout_failure_rate", "api_error_rate"],
        fingerprint="seed-incident-checkout-outage",
        detected_at=t_0 + datetime.timedelta(minutes=15),
        investigation_started_at=t_0 + datetime.timedelta(minutes=16),
        confidence=0.96,
        estimated_revenue_impact=Decimal("12500.00"),
        estimated_orders_affected=148,
        estimated_users_affected=420,
        estimated_support_impact=25,
        created_at=t_0 + datetime.timedelta(minutes=15),
    )
    # Associate anomalies via secondary table
    incident.anomalies.extend([anomaly_checkout, anomaly_api])
    db.add(incident)
    db.flush()

    # 11. Incident Evidence
    ev_deploy = IncidentEvidence(
        id=uuid.uuid4(),
        incident_id=incident.id,
        source_type=EvidenceSourceType.DEPLOYMENT,
        source_id=str(deployment.id),
        title="Recent deployment checkout-service v4.8.2",
        summary="Service checkout-service deployed 5 minutes prior to initial error spike.",
        observed_at=deployment.deployed_at,
        relevance_score=0.95,
        evidence_metadata={"service": "checkout-service", "version": "v4.8.2"},
    )
    ev_event = IncidentEvidence(
        id=uuid.uuid4(),
        incident_id=incident.id,
        source_type=EvidenceSourceType.SYSTEM_EVENT,
        source_id=str(event1.id),
        title="Database connection pool exhaustion on checkout-service",
        summary="100/100 connections acquired without release, causing upstream timeout cascades.",
        observed_at=event1.timestamp,
        relevance_score=0.98,
        evidence_metadata={"event_type": "DATABASE_ERROR"},
    )
    ev_metric = IncidentEvidence(
        id=uuid.uuid4(),
        incident_id=incident.id,
        source_type=EvidenceSourceType.METRIC,
        source_id=str(checkout_metric.id),
        title="Checkout failure rate anomalous surge",
        summary="Sustained 42.8% checkout failure rate coinciding with pool exhaustion.",
        observed_at=checkout_metric.timestamp,
        relevance_score=0.92,
        evidence_metadata={"metric": "checkout_failure_rate"},
    )
    db.add_all([ev_deploy, ev_event, ev_metric])
    db.flush()

    # 12. Investigation & Hypotheses
    investigation = Investigation(
        id=uuid.uuid4(),
        incident_id=incident.id,
        status=InvestigationStatus.RUNNING,
        started_at=t_0 + datetime.timedelta(minutes=16),
        summary="Investigating causal links between deployment v4.8.2 and connection pool exhaustion.",
        root_cause=None,
        confidence=0.91,
        uncertainty=0.09,
    )
    db.add(investigation)
    db.flush()

    hypo1 = InvestigationHypothesis(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        title="Deployment v4.8.2 introduced unclosed connection leak in payment commit step",
        description="Code diff in commit a1c8f90 omitted session.close() in exception handling block of checkout service.",
        status=HypothesisStatus.SUPPORTED,
        confidence=0.92,
        supporting_evidence_summary="Correlated deployment timestamp (14:00 UTC) with immediate connection pool saturation (14:05 UTC).",
    )
    hypo2 = InvestigationHypothesis(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        title="External payment provider experiencing widespread downtime",
        description="Third-party payment gateway latency caused connection hold time to spike.",
        status=HypothesisStatus.REJECTED,
        confidence=0.15,
        supporting_evidence_summary="Payment gateway status page reports all APIs nominal; internal connection exhaustion occurred before gateway call.",
    )
    db.add_all([hypo1, hypo2])
    db.flush()

    # 13. Recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback checkout-service to stable release v4.8.1",
        description="Execute automated rollback to v4.8.1 to restore healthy connection pool limits and verify checkout error rate return to <0.05%.",
        priority=TicketPriority.URGENT,
        risk_level=SeverityLevel.LOW,
        expected_impact="Immediately restores database connection availability and reduces checkout failure rate to nominal (<0.05%).",
        status=RecommendationStatus.PROPOSED,
    )
    db.add(rec)
    db.flush()

    # 14. Action (Awaiting Human-in-the-loop Approval)
    action = Action(
        id=uuid.uuid4(),
        recommendation_id=rec.id,
        incident_id=incident.id,
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        description="Roll back production deployment of checkout-service to image tag v4.8.1 in cluster us-east-1.",
        risk_level=SeverityLevel.LOW,
        approval_status=ActionApprovalStatus.PENDING,
        execution_status=ActionExecutionStatus.NOT_STARTED,
        requested_at=t_0 + datetime.timedelta(minutes=20),
        requested_by="aegis-investigator-agent",
        approved_by=None,
        execution_result=None,
        action_metadata={"target_service": "checkout-service", "target_version": "v4.8.1"},
    )
    db.add(action)
    db.flush()

    # 15. Comprehensive Audit Trail
    audit_events = [
        (
            "DEPLOYMENT_REGISTERED",
            "Deployment",
            str(deployment.id),
            AuditActorType.SYSTEM,
            "ci-runner",
        ),
        (
            "ANOMALY_DETECTED",
            "Anomaly",
            str(anomaly_checkout.id),
            AuditActorType.AGENT,
            "aegis-detector",
        ),
        (
            "INCIDENT_CREATED",
            "Incident",
            str(incident.id),
            AuditActorType.AGENT,
            "aegis-correlator",
        ),
        (
            "INVESTIGATION_STARTED",
            "Investigation",
            str(investigation.id),
            AuditActorType.AGENT,
            "aegis-investigator",
        ),
        (
            "RECOMMENDATION_CREATED",
            "Recommendation",
            str(rec.id),
            AuditActorType.AGENT,
            "aegis-investigator",
        ),
        ("ACTION_PROPOSED", "Action", str(action.id), AuditActorType.AGENT, "aegis-investigator"),
    ]

    for action_name, res_type, res_id, actor_type, actor_id in audit_events:
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            company_id=company.id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action_name,
            resource_type=res_type,
            resource_id=res_id,
            timestamp=t_0 + datetime.timedelta(minutes=20),
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            audit_metadata={"environment": "production", "status": "success"},
        )
        db.add(audit_entry)

    db.commit()
    logger.info("Aegis database seeding completed successfully.")

    return {
        "company_id": str(company.id),
        "incident_id": str(incident.id),
        "investigation_id": str(investigation.id),
        "recommendation_id": str(rec.id),
        "action_id": str(action.id),
        "metrics_count": len(metric_entities),
    }


if __name__ == "__main__":
    import app.models  # noqa: F401
    from app.database.base import Base
    from app.database.session import get_engine

    setup_logging()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory()
    with session_factory() as session:
        result = seed_database(session)
        print("Seeded successfully:", result)
