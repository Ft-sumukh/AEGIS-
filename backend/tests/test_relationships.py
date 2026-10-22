"""Tests for entity relationships, many-to-many associations, and cascade rules."""

import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.customer import Customer
from app.models.enums import (
    AnomalyStatus,
    AuditActorType,
    DetectorType,
    EvidenceSourceType,
    IncidentStatus,
    OrderStatus,
    RecommendationStatus,
    SeverityLevel,
    TicketPriority,
)
from app.models.incident import Incident, IncidentEvidence
from app.models.investigation import Investigation
from app.models.order import Order, OrderItem
from app.models.recommendation import Recommendation


def test_incident_anomalies_many_to_many(db_session: Session) -> None:
    """Verify Incident <-> Anomaly many-to-many association."""
    company = Company(name="Rel Corp", slug="rel-corp")
    db_session.add(company)
    db_session.flush()

    now = datetime.datetime.now(datetime.UTC)
    anomaly_1 = Anomaly(
        company_id=company.id,
        metric_name="latency",
        detected_at=now,
        observed_value=500.0,
        expected_value=100.0,
        deviation=400.0,
        detector_type=DetectorType.THRESHOLD,
        severity=SeverityLevel.HIGH,
        confidence=0.9,
        explanation="Latency spike",
        status=AnomalyStatus.CORRELATED,
    )
    anomaly_2 = Anomaly(
        company_id=company.id,
        metric_name="error_rate",
        detected_at=now,
        observed_value=15.0,
        expected_value=0.1,
        deviation=14.9,
        detector_type=DetectorType.Z_SCORE,
        severity=SeverityLevel.CRITICAL,
        confidence=0.95,
        explanation="5xx errors spike",
        status=AnomalyStatus.CORRELATED,
    )
    db_session.add_all([anomaly_1, anomaly_2])
    db_session.flush()

    incident = Incident(
        company_id=company.id,
        title="Cascading Outage",
        summary="Service latency caused downstream 5xx errors",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.OPEN,
        detected_at=now,
    )
    incident.anomalies.extend([anomaly_1, anomaly_2])
    db_session.add(incident)
    db_session.commit()

    retrieved = db_session.scalar(select(Incident).where(Incident.id == incident.id))
    assert retrieved is not None
    assert len(retrieved.anomalies) == 2
    anomaly_names = {a.metric_name for a in retrieved.anomalies}
    assert "latency" in anomaly_names
    assert "error_rate" in anomaly_names

    # Check reverse relationship
    retrieved_anomaly = db_session.scalar(select(Anomaly).where(Anomaly.id == anomaly_1.id))
    assert retrieved_anomaly is not None
    assert len(retrieved_anomaly.incidents) == 1
    assert retrieved_anomaly.incidents[0].id == incident.id


def test_order_cascade_deletes_items(db_session: Session) -> None:
    """Verify deleting an Order cascades to delete all associated OrderItems."""
    company = Company(name="Shop Corp", slug="shop-corp")
    db_session.add(company)
    db_session.flush()

    customer = Customer(company_id=company.id, external_reference="C-DEL", name="Delete Shopper")
    db_session.add(customer)
    db_session.flush()

    order = Order(
        company_id=company.id,
        customer_id=customer.id,
        external_reference="ORD-CASCADE",
        status=OrderStatus.PENDING,
        currency="USD",
        total_amount=Decimal("100.00"),
        ordered_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_reference="PROD-DEL",
        quantity=2,
        unit_price=Decimal("50.00"),
        total_price=Decimal("100.00"),
    )
    db_session.add(item)
    db_session.commit()

    item_id = item.id
    db_session.delete(order)
    db_session.commit()

    # Order item should have been deleted
    deleted_item = db_session.scalar(select(OrderItem).where(OrderItem.id == item_id))
    assert deleted_item is None


def test_incident_cascade_deletes_evidence_and_investigations(db_session: Session) -> None:
    """Verify deleting an Incident cascades to delete evidence, investigations, and recommendations."""
    company = Company(name="Cascade Corp", slug="cascade-corp")
    db_session.add(company)
    db_session.flush()

    now = datetime.datetime.now(datetime.UTC)
    incident = Incident(
        company_id=company.id,
        title="Incident To Delete",
        summary="Testing cascades",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        detected_at=now,
    )
    db_session.add(incident)
    db_session.flush()

    evidence = IncidentEvidence(
        incident_id=incident.id,
        source_type=EvidenceSourceType.METRIC,
        title="Evidence Item",
        summary="Metric surge",
        observed_at=now,
        relevance_score=1.0,
    )
    investigation = Investigation(
        incident_id=incident.id,
        summary="Investigation To Delete",
    )
    db_session.add_all([evidence, investigation])
    db_session.flush()

    rec = Recommendation(
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Recommendation To Delete",
        description="Plan",
        priority=TicketPriority.MEDIUM,
        risk_level=SeverityLevel.LOW,
        expected_impact="High",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(rec)
    db_session.commit()

    evidence_id = evidence.id
    investigation_id = investigation.id
    rec_id = rec.id

    db_session.delete(incident)
    db_session.commit()

    assert (
        db_session.scalar(select(IncidentEvidence).where(IncidentEvidence.id == evidence_id))
        is None
    )
    assert (
        db_session.scalar(select(Investigation).where(Investigation.id == investigation_id)) is None
    )
    assert db_session.scalar(select(Recommendation).where(Recommendation.id == rec_id)) is None


def test_audit_logs_not_cascade_deleted_with_company(db_session: Session) -> None:
    """CRITICAL COMPLIANCE TEST: Deleting a company must NOT delete its audit trail."""
    company = Company(name="Doomed Corp", slug="doomed-corp")
    db_session.add(company)
    db_session.flush()

    audit = AuditLog(
        company_id=company.id,
        actor_type=AuditActorType.USER,
        actor_id="admin-user",
        action="COMPANY_MODIFIED",
        resource_type="Company",
        resource_id=str(company.id),
    )
    db_session.add(audit)
    db_session.commit()

    audit_id = audit.id
    company_id = company.id

    # Delete company
    db_session.delete(company)
    db_session.commit()

    # Verify audit record still exists, with company_id set to null or preserved
    preserved_audit = db_session.scalar(select(AuditLog).where(AuditLog.id == audit_id))
    assert preserved_audit is not None
    assert preserved_audit.company_id is None
    assert preserved_audit.resource_id == str(company_id)
