"""Tests for database referential integrity, constraints, and transaction rollback."""

import datetime
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.company import Company
from app.models.enums import (
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionType,
    OrderStatus,
    RecommendationStatus,
    SeverityLevel,
    TicketPriority,
)
from app.models.order import Order, OrderItem
from app.models.recommendation import Recommendation


def test_order_nonexistent_customer_rejected(db_session: Session) -> None:
    """Verify cannot create an Order referencing a non-existent Customer."""
    company = Company(name="Integrity Corp", slug="integrity-corp")
    db_session.add(company)
    db_session.flush()

    non_existent_customer_id = uuid.uuid4()
    order = Order(
        company_id=company.id,
        customer_id=non_existent_customer_id,
        external_reference="ORD-INVALID",
        status=OrderStatus.PENDING,
        currency="USD",
        total_amount=Decimal("50.00"),
        ordered_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(order)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_recommendation_nonexistent_investigation_rejected(db_session: Session) -> None:
    """Verify cannot create a Recommendation referencing a non-existent Investigation."""
    company = Company(name="Integrity Corp 2", slug="integrity-corp-2")
    db_session.add(company)
    db_session.flush()

    fake_id = uuid.uuid4()
    fake_incident_id = uuid.uuid4()

    rec = Recommendation(
        investigation_id=fake_id,
        incident_id=fake_incident_id,
        title="Invalid Rec",
        description="Should fail",
        priority=TicketPriority.LOW,
        risk_level=SeverityLevel.LOW,
        expected_impact="None",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(rec)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_action_nonexistent_recommendation_rejected(db_session: Session) -> None:
    """Verify cannot create an Action referencing a non-existent Recommendation."""
    fake_id = uuid.uuid4()
    fake_incident_id = uuid.uuid4()

    action = Action(
        recommendation_id=fake_id,
        incident_id=fake_incident_id,
        action_type=ActionType.CREATE_TICKET,
        description="Invalid action",
        risk_level=SeverityLevel.LOW,
        approval_status=ActionApprovalStatus.NOT_REQUIRED,
        execution_status=ActionExecutionStatus.NOT_STARTED,
        requested_by="tester",
    )
    db_session.add(action)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_order_item_negative_quantity_rejected(db_session: Session) -> None:
    """Verify check constraint rejects zero or negative quantity in OrderItem."""
    company = Company(name="Quantity Corp", slug="qty-corp")
    db_session.add(company)
    db_session.flush()

    from app.models.customer import Customer

    cust = Customer(company_id=company.id, external_reference="C-QTY", name="Qty User")
    db_session.add(cust)
    db_session.flush()

    order = Order(
        company_id=company.id,
        customer_id=cust.id,
        external_reference="ORD-QTY",
        status=OrderStatus.PENDING,
        currency="USD",
        total_amount=Decimal("10.00"),
        ordered_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(order)
    db_session.flush()

    invalid_item = OrderItem(
        order_id=order.id,
        product_reference="SKU-NEG",
        quantity=-2,  # Invalid by CheckConstraint("quantity > 0")
        unit_price=Decimal("5.00"),
        total_price=Decimal("-10.00"),
    )
    db_session.add(invalid_item)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_transaction_rollback_recovers_cleanly(db_session: Session) -> None:
    """Verify database recovers and allows valid operations after a failed transaction."""
    comp1 = Company(name="Valid Co", slug="valid-co")
    db_session.add(comp1)
    db_session.commit()

    # Intentionally trigger an error
    comp_dup = Company(name="Duplicate Co", slug="valid-co")
    db_session.add(comp_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Subsequent valid operation must succeed
    comp2 = Company(name="Another Valid Co", slug="another-valid-co")
    db_session.add(comp2)
    db_session.commit()

    assert db_session.scalar(select(Company).where(Company.slug == "another-valid-co")) is not None
