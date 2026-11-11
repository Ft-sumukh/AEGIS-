"""Unit tests for service dependency discovery and trace-derived health metrics."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.analytics.service_dependencies import ServiceDependencyAnalyzer
from app.analytics.service_trace_health import ServiceTraceHealthAnalyzer
from app.models.company import Company
from app.models.trace import TraceSpan


def test_service_dependency_graph_discovery(db_session: Session) -> None:
    """Verify directed service dependency graph extraction from trace span parent-child relationships."""
    company = Company(
        id=uuid.uuid4(),
        name="Graph Corp",
        slug=f"graph-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    now = datetime.now(UTC)

    # Ingest 10 traces where api-gateway calls cart-service, and cart-service calls payment-gateway
    for i in range(10):
        trace_id = f"dep-trace-{i:03d}"
        t_start = now - timedelta(minutes=10 - i)

        root = TraceSpan(
            id=uuid.uuid4(),
            company_id=company.id,
            trace_id=trace_id,
            span_id=f"root-{i}",
            parent_span_id=None,
            timestamp_start=t_start,
            timestamp_end=t_start + timedelta(milliseconds=200),
            duration_ms=200.0,
            service_name="api-gateway",
            operation_name="POST /checkout",
            environment="production",
            status="OK",
        )
        cart = TraceSpan(
            id=uuid.uuid4(),
            company_id=company.id,
            trace_id=trace_id,
            span_id=f"cart-{i}",
            parent_span_id=f"root-{i}",
            timestamp_start=t_start + timedelta(milliseconds=10),
            timestamp_end=t_start + timedelta(milliseconds=180),
            duration_ms=170.0,
            service_name="cart-service",
            operation_name="checkout",
            environment="production",
            status="ERROR" if i >= 8 else "OK",  # 2 errors out of 10
            http_status_code=500 if i >= 8 else 200,
        )
        pg = TraceSpan(
            id=uuid.uuid4(),
            company_id=company.id,
            trace_id=trace_id,
            span_id=f"pg-{i}",
            parent_span_id=f"cart-{i}",
            timestamp_start=t_start + timedelta(milliseconds=20),
            timestamp_end=t_start + timedelta(milliseconds=150),
            duration_ms=130.0,
            service_name="payment-gateway",
            operation_name="authorize",
            environment="production",
            status="ERROR" if i >= 8 else "OK",
            http_status_code=504 if i >= 8 else 200,
        )
        db_session.add_all([root, cart, pg])

    db_session.commit()

    graph = ServiceDependencyAnalyzer.get_dependency_graph(
        db=db_session,
        environment="production",
        time_window_hours=1,
    )

    assert len(graph.nodes) >= 3
    node_names = [n["service"] for n in graph.nodes]
    assert "api-gateway" in node_names
    assert "cart-service" in node_names
    assert "payment-gateway" in node_names

    # Check edges
    edge_pairs = [(e.source_service, e.target_service) for e in graph.edges]
    assert ("api-gateway", "cart-service") in edge_pairs
    assert ("cart-service", "payment-gateway") in edge_pairs

    # Verify edge metrics
    cart_to_pg = next(e for e in graph.edges if e.source_service == "cart-service" and e.target_service == "payment-gateway")
    assert cart_to_pg.request_count == 10
    assert cart_to_pg.error_count == 2
    assert cart_to_pg.error_rate == 0.2
    assert cart_to_pg.p50_latency_ms == 130.0


def test_service_trace_health_analyzer(db_session: Session) -> None:
    """Verify trace health status calculations (HEALTHY vs DEGRADED)."""
    company = Company(
        id=uuid.uuid4(),
        name="Health Corp",
        slug=f"health-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    now = datetime.now(UTC)

    # Ingest healthy spans for search-service
    for i in range(20):
        span = TraceSpan(
            id=uuid.uuid4(),
            company_id=company.id,
            trace_id=f"health-trace-{i}",
            span_id=f"health-span-{i}",
            timestamp_start=now - timedelta(minutes=5),
            timestamp_end=now - timedelta(minutes=5) + timedelta(milliseconds=45),
            duration_ms=45.0,
            service_name="search-service",
            operation_name="GET /search",
            environment="production",
            status="OK",
        )
        db_session.add(span)

    # Ingest failing spans for auth-service (60% errors)
    for i in range(10):
        span = TraceSpan(
            id=uuid.uuid4(),
            company_id=company.id,
            trace_id=f"auth-trace-{i}",
            span_id=f"auth-span-{i}",
            timestamp_start=now - timedelta(minutes=5),
            timestamp_end=now - timedelta(minutes=5) + timedelta(milliseconds=600),
            duration_ms=600.0,
            service_name="auth-service",
            operation_name="POST /login",
            environment="production",
            status="ERROR" if i < 6 else "OK",
            http_status_code=500 if i < 6 else 200,
        )
        db_session.add(span)

    db_session.commit()

    search_health = ServiceTraceHealthAnalyzer.get_health(
        db=db_session,
        service_name="search-service",
        environment="production",
        time_window_hours=1,
    )
    assert search_health.service_name == "search-service"
    assert search_health.request_count == 20
    assert search_health.error_count == 0
    assert search_health.error_rate == 0.0
    assert search_health.health_status == "HEALTHY"

    auth_health = ServiceTraceHealthAnalyzer.get_health(
        db=db_session,
        service_name="auth-service",
        environment="production",
        time_window_hours=1,
    )
    assert auth_health.service_name == "auth-service"
    assert auth_health.request_count == 10
    assert auth_health.error_count == 6
    assert auth_health.error_rate == 0.6
    assert auth_health.health_status in ("DEGRADED", "FAILED")
