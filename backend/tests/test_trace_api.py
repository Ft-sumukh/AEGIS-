"""Integration tests for all Phase 2 Distributed Tracing and Telemetry REST endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.trace import TraceSpan


def test_trace_list_and_filters(client: TestClient, seeded_db_session: Session) -> None:
    """Verify GET /api/v1/traces listing, filtering, and pagination."""
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    now = datetime.now(UTC)
    trace_id_1 = "api-trace-list-01"
    trace_id_2 = "api-trace-list-02"

    span1 = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id_1,
        span_id="s1",
        parent_span_id=None,
        timestamp_start=now,
        timestamp_end=now + timedelta(milliseconds=120),
        duration_ms=120.0,
        service_name="frontend-web",
        operation_name="GET /",
        environment="production",
        status="OK",
    )
    span2 = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id_2,
        span_id="s2",
        parent_span_id=None,
        timestamp_start=now,
        timestamp_end=now + timedelta(milliseconds=850),
        duration_ms=850.0,
        service_name="payment-gateway",
        operation_name="POST /charge",
        environment="production",
        status="ERROR",
        http_status_code=500,
    )
    seeded_db_session.add_all([span1, span2])
    seeded_db_session.commit()

    # List all traces
    res = client.get("/api/v1/traces")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2

    # Filter by service
    res_svc = client.get("/api/v1/traces?service=payment-gateway")
    assert res_svc.status_code == 200
    assert len(res_svc.json()["items"]) >= 1
    assert any(t["trace_id"] == trace_id_2 for t in res_svc.json()["items"])

    # Filter by status ERROR
    res_err = client.get("/api/v1/traces?status=ERROR")
    assert res_err.status_code == 200
    assert any(t["trace_id"] == trace_id_2 for t in res_err.json()["items"])

    # Filter by min_duration_ms
    res_dur = client.get("/api/v1/traces?min_duration_ms=500")
    assert res_dur.status_code == 200
    assert all(t["duration_ms"] >= 500.0 for t in res_dur.json()["items"])


def test_get_trace_tree_detail(client: TestClient, seeded_db_session: Session) -> None:
    """Verify GET /api/v1/traces/{trace_id} returns hierarchical tree with critical path and error analysis."""
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    trace_id = "api-trace-detail-01"
    now = datetime.now(UTC)

    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="root-span",
        parent_span_id=None,
        timestamp_start=now,
        timestamp_end=now + timedelta(milliseconds=600),
        duration_ms=600.0,
        service_name="api-gateway",
        operation_name="POST /checkout",
        status="ERROR",
    )
    child = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="child-span",
        parent_span_id="root-span",
        timestamp_start=now + timedelta(milliseconds=20),
        timestamp_end=now + timedelta(milliseconds=580),
        duration_ms=560.0,
        service_name="checkout-service",
        operation_name="process_order",
        status="ERROR",
        http_status_code=500,
    )
    seeded_db_session.add_all([root, child])
    seeded_db_session.commit()

    res = client.get(f"/api/v1/traces/{trace_id}")
    assert res.status_code == 200
    tree = res.json()
    assert tree["trace_id"] == trace_id
    assert tree["spans_count"] == 2
    assert tree["root_span"]["span_id"] == "root-span"
    assert len(tree["root_span"]["children"]) == 1
    assert tree["critical_path"] is not None
    assert tree["error_propagation"] is not None
    assert tree["error_propagation"]["has_errors"] is True


def test_trace_ingestion_api(client: TestClient, seeded_db_session: Session) -> None:
    """Verify POST /api/v1/telemetry/traces batch span ingestion."""
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    now = datetime.now(UTC)
    payload = {
        "company_id": str(company.id),
        "source": "otel_collector",
        "spans": [
            {
                "trace_id": "ingest-trace-001",
                "span_id": "ingest-span-001",
                "timestamp_start": now.isoformat(),
                "timestamp_end": (now + timedelta(milliseconds=150)).isoformat(),
                "duration_ms": 150.0,
                "service_name": "inventory-service",
                "operation_name": "GET /stock",
                "status": "OK",
            }
        ],
    }

    res = client.post("/api/v1/telemetry/traces", json=payload)
    assert res.status_code in (200, 201)
    result = res.json()
    assert result["accepted"] == 1
    assert result["rejected"] == 0

    # Verify span is stored in database
    span_db = seeded_db_session.scalar(
        select(TraceSpan).where(TraceSpan.trace_id == "ingest-trace-001")
    )
    assert span_db is not None
    assert span_db.service_name == "inventory-service"


def test_incident_trace_correlation_endpoints(
    client: TestClient, seeded_db_session: Session
) -> None:
    """Verify GET and POST trace correlation endpoints for incidents."""
    company = seeded_db_session.scalar(select(Company).limit(1))
    assert company is not None

    # Create incident
    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Payment Service Degradation",
        summary="High latency observed on payment flows",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.INVESTIGATING,
        category="PERFORMANCE",
        affected_systems=["payment-gateway"],
        detected_at=datetime.now(UTC),
    )
    seeded_db_session.add(incident)
    seeded_db_session.commit()

    # GET /api/v1/incidents/{id}/traces
    res_get = client.get(f"/api/v1/incidents/{incident.id}/traces")
    assert res_get.status_code == 200
    corr_data = res_get.json()
    assert corr_data["incident_id"] == str(incident.id)
    assert "non_causal_synthesis" in corr_data

    # POST /api/v1/incidents/{id}/correlate-traces (attach evidence)
    res_post = client.post(f"/api/v1/incidents/{incident.id}/correlate-traces")
    assert res_post.status_code == 200
    attached = res_post.json()
    assert isinstance(attached, list)
    assert len(attached) >= 1
