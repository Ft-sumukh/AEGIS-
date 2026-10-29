"""Tests for the TraceSpan ORM model, relationships, indexes, and constraints."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.trace import TraceSpan


def test_trace_span_creation_and_attributes(db_session: Session) -> None:
    """Verify TraceSpan creation with all OpenTelemetry and Group 7 sanitized fields."""
    company = Company(
        id=uuid.uuid4(),
        name="Telemetry Corp",
        slug=f"telemetry-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    start = datetime.now(UTC)
    end = start + timedelta(milliseconds=125)

    span = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        parent_span_id=None,  # Root span
        timestamp_start=start,
        timestamp_end=end,
        duration_ms=125.0,
        service_name="cart-service",
        service_version="v4.8.2",
        environment="production",
        operation_name="POST /checkout",
        span_kind="SERVER",
        status="OK",
        http_method="POST",
        http_route="/checkout",
        http_status_code=200,
        sanitized_attributes={
            "http.target": "/checkout",
            "sanitized": True,
        },
    )
    db_session.add(span)
    db_session.commit()

    fetched = db_session.scalar(select(TraceSpan).where(TraceSpan.id == span.id))
    assert fetched is not None
    assert fetched.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert fetched.span_id == "00f067aa0ba902b7"
    assert fetched.parent_span_id is None
    assert fetched.duration_ms == 125.0
    assert fetched.service_name == "cart-service"
    assert fetched.sanitized_attributes["sanitized"] is True
    assert fetched.company_id == company.id


def test_trace_span_parent_child_relationship(db_session: Session) -> None:
    """Verify trace hierarchy with root and child spans."""
    company = Company(
        id=uuid.uuid4(),
        name="Hierarchy Corp",
        slug=f"hierarchy-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    trace_id = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    start = datetime.now(UTC)

    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="root-span-1234",
        parent_span_id=None,
        timestamp_start=start,
        timestamp_end=start + timedelta(milliseconds=200),
        duration_ms=200.0,
        service_name="api-gateway",
        operation_name="GET /items",
        status="OK",
    )
    child = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="child-span-5678",
        parent_span_id="root-span-1234",
        timestamp_start=start + timedelta(milliseconds=10),
        timestamp_end=start + timedelta(milliseconds=180),
        duration_ms=170.0,
        service_name="inventory-service",
        operation_name="query_stock",
        status="OK",
    )
    db_session.add_all([root, child])
    db_session.commit()

    spans = db_session.scalars(select(TraceSpan).where(TraceSpan.trace_id == trace_id)).all()
    assert len(spans) == 2
    root_found = next(s for s in spans if s.parent_span_id is None)
    child_found = next(s for s in spans if s.parent_span_id is not None)
    assert child_found.parent_span_id == root_found.span_id


def test_trace_span_company_cascade_delete(db_session: Session) -> None:
    """Verify deleting a company cascades and removes associated trace spans."""
    company = Company(
        id=uuid.uuid4(),
        name="Cascade Corp",
        slug=f"cascade-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    span = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id="cascade-trace-123",
        span_id="cascade-span-123",
        timestamp_start=datetime.now(UTC),
        timestamp_end=datetime.now(UTC) + timedelta(milliseconds=50),
        duration_ms=50.0,
        service_name="order-service",
        operation_name="cancel",
        status="OK",
    )
    db_session.add(span)
    db_session.commit()

    # Verify span exists
    assert db_session.scalar(select(TraceSpan).where(TraceSpan.id == span.id)) is not None

    # Delete company
    db_session.delete(company)
    db_session.commit()

    # Verify span was cascade deleted
    assert db_session.scalar(select(TraceSpan).where(TraceSpan.id == span.id)) is None
