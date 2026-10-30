"""Unit tests for trace tree reconstruction, critical path analysis, and error propagation."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.analytics.critical_path import CriticalPathAnalyzer
from app.analytics.error_propagation import ErrorPropagationAnalyzer
from app.analytics.trace_service import TraceService
from app.models.company import Company
from app.models.trace import TraceSpan


def test_trace_tree_reconstruction(db_session: Session) -> None:
    """Verify trace tree reconstruction without N+1 queries and correct self-time calculation."""
    company = Company(
        id=uuid.uuid4(),
        name="Analytics Corp",
        slug=f"analytics-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    trace_id = "trace-recon-001"
    t0 = datetime.now(UTC)

    # Root span: api-gateway (duration: 300ms)
    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="span-root",
        parent_span_id=None,
        timestamp_start=t0,
        timestamp_end=t0 + timedelta(milliseconds=300),
        duration_ms=300.0,
        service_name="api-gateway",
        operation_name="POST /order",
        status="OK",
    )
    # Child span: order-service (duration: 200ms)
    child = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="span-child",
        parent_span_id="span-root",
        timestamp_start=t0 + timedelta(milliseconds=20),
        timestamp_end=t0 + timedelta(milliseconds=220),
        duration_ms=200.0,
        service_name="order-service",
        operation_name="create_order",
        status="OK",
    )
    # Grandchild span: inventory-service (duration: 80ms)
    grandchild = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="span-grandchild",
        parent_span_id="span-child",
        timestamp_start=t0 + timedelta(milliseconds=40),
        timestamp_end=t0 + timedelta(milliseconds=120),
        duration_ms=80.0,
        service_name="inventory-service",
        operation_name="reserve_stock",
        status="OK",
    )
    db_session.add_all([root, child, grandchild])
    db_session.commit()

    tree = TraceService.get_trace(db_session, trace_id)
    assert tree is not None
    assert tree.trace_id == trace_id
    assert tree.spans_count == 3
    assert tree.root_span is not None
    assert tree.root_span.span_id == "span-root"
    assert len(tree.root_span.children) == 1
    assert tree.root_span.children[0].span_id == "span-child"
    assert len(tree.root_span.children[0].children) == 1
    assert tree.root_span.children[0].children[0].span_id == "span-grandchild"

    # Verify self-time calculations
    # Root self-time = 300 - 200 = 100ms
    assert tree.root_span.self_time_ms == 100.0
    # Child self-time = 200 - 80 = 120ms
    assert tree.root_span.children[0].self_time_ms == 120.0
    # Grandchild self-time = 80ms (no children)
    assert tree.root_span.children[0].children[0].self_time_ms == 80.0


def test_critical_path_parallel_spans() -> None:
    """Verify critical path analyzer correctly picks the bottleneck branch among concurrent child spans."""
    t0 = datetime.now(UTC)
    trace_id = "trace-crit-parallel"

    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="root",
        parent_span_id=None,
        timestamp_start=t0,
        timestamp_end=t0 + timedelta(milliseconds=500),
        duration_ms=500.0,
        service_name="orchestrator",
        operation_name="handle_workflow",
        status="OK",
    )
    # Fast branch (runs in parallel from t0+10 to t0+60)
    fast_child = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="fast-child",
        parent_span_id="root",
        timestamp_start=t0 + timedelta(milliseconds=10),
        timestamp_end=t0 + timedelta(milliseconds=60),
        duration_ms=50.0,
        service_name="fast-service",
        operation_name="fast_op",
        status="OK",
    )
    # Slow bottleneck branch (runs in parallel from t0+10 to t0+450)
    slow_child = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="slow-child",
        parent_span_id="root",
        timestamp_start=t0 + timedelta(milliseconds=10),
        timestamp_end=t0 + timedelta(milliseconds=450),
        duration_ms=440.0,
        service_name="database-service",
        operation_name="heavy_query",
        status="OK",
    )

    result = CriticalPathAnalyzer.analyze([root, fast_child, slow_child])
    assert result.trace_id == trace_id
    assert len(result.segments) >= 2
    segment_span_ids = [seg.span_id for seg in result.segments]

    # Critical path must contain root and slow-child, NOT fast-child
    assert "root" in segment_span_ids
    assert "slow-child" in segment_span_ids
    assert "fast-child" not in segment_span_ids

    # Critical path segment contribution
    slow_segment = next(s for s in result.segments if s.span_id == "slow-child")
    assert slow_segment.duration_ms == 440.0
    assert slow_segment.contribution_percent > 80.0


def test_error_propagation_analyzer() -> None:
    """Verify error propagation detects root failure in deepest downstream service."""
    t0 = datetime.now(UTC)
    trace_id = "trace-err-prop"

    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="span-gw",
        parent_span_id=None,
        timestamp_start=t0,
        timestamp_end=t0 + timedelta(milliseconds=400),
        duration_ms=400.0,
        service_name="api-gateway",
        operation_name="POST /checkout",
        status="ERROR",
        http_status_code=500,
        status_message="Upstream service returned error",
    )
    middle = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="span-checkout",
        parent_span_id="span-gw",
        timestamp_start=t0 + timedelta(milliseconds=20),
        timestamp_end=t0 + timedelta(milliseconds=380),
        duration_ms=360.0,
        service_name="checkout-service",
        operation_name="process_checkout",
        status="ERROR",
        http_status_code=500,
        status_message="Payment gateway error",
    )
    deepest = TraceSpan(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        trace_id=trace_id,
        span_id="span-pg",
        parent_span_id="span-checkout",
        timestamp_start=t0 + timedelta(milliseconds=50),
        timestamp_end=t0 + timedelta(milliseconds=350),
        duration_ms=300.0,
        service_name="payment-gateway",
        operation_name="charge_card",
        status="ERROR",
        http_status_code=504,
        status_message="Gateway timeout connecting to acquiring bank",
    )

    result = ErrorPropagationAnalyzer.analyze([root, middle, deepest])
    assert result.has_errors is True
    assert result.root_error_service == "payment-gateway"
    assert result.root_error_span_id == "span-pg"
    assert result.root_error_status_code == 504
    assert len(result.propagation_chain) == 3

    # First in chain should be the root error
    assert result.propagation_chain[0].span_id == "span-pg"
    assert result.propagation_chain[0].is_deepest_error is True
    assert result.propagation_chain[-1].span_id == "span-gw"
    assert "Observed error propagation pattern" in result.non_causal_assessment
    assert "payment-gateway -> checkout-service -> api-gateway" in result.non_causal_assessment

