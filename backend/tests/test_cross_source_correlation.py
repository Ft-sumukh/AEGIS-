"""Unit tests for cross-source correlation linking deployments, traces, metrics, and incident evidence."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.analytics.cross_correlation import CrossSourceCorrelator
from app.models.company import Company
from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.events import Deployment
from app.models.incident import Incident, IncidentEvidence
from app.models.trace import TraceSpan


def test_cross_source_correlation_and_evidence_attachment(db_session: Session) -> None:
    """Verify cross-source correlation links deployments to traces and attaches structured evidence."""
    company = Company(
        id=uuid.uuid4(),
        name="Correlation Corp",
        slug=f"corr-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    now = datetime.now(UTC)
    t_deploy = now - timedelta(minutes=25)
    t_incident = now - timedelta(minutes=15)

    # 1. Preceding Deployment
    deployment = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="cart-service",
        version="v4.8.2",
        environment="production",
        deployed_at=t_deploy,
        deployed_by="ci-pipeline",
        status="SUCCESS",
    )
    db_session.add(deployment)

    # 2. Open Incident
    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Checkout Latency and Error Anomaly",
        summary="Surge in checkout latency and 500 errors",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.INVESTIGATING,
        category="PERFORMANCE",
        affected_systems=["cart-service", "payment-gateway"],
        affected_metrics=["p95_latency_ms", "http_5xx_rate"],
        detected_at=t_incident,
    )
    db_session.add(incident)
    db_session.commit()

    # 3. Slow and Failed Trace Spans around incident window
    trace_id = "trace-corr-101"
    root_span = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="span-root",
        parent_span_id=None,
        timestamp_start=t_incident + timedelta(minutes=1),
        timestamp_end=t_incident + timedelta(minutes=1, milliseconds=1200),
        duration_ms=1200.0,
        service_name="cart-service",
        operation_name="POST /checkout",
        environment="production",
        status="ERROR",
        http_status_code=500,
    )
    child_span = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="span-child",
        parent_span_id="span-root",
        timestamp_start=t_incident + timedelta(minutes=1, milliseconds=50),
        timestamp_end=t_incident + timedelta(minutes=1, milliseconds=1150),
        duration_ms=1100.0,
        service_name="payment-gateway",
        operation_name="process_payment",
        environment="production",
        status="ERROR",
        http_status_code=504,
        status_message="Upstream provider timeout",
    )
    db_session.add_all([root_span, child_span])
    db_session.commit()

    # Run correlation analysis
    corr_result = CrossSourceCorrelator.correlate_incident(db_session, incident.id)
    assert "error" not in corr_result
    assert corr_result["incident_id"] == str(incident.id)
    assert corr_result["lead_deployment"] is not None
    assert corr_result["lead_deployment"]["version"] == "v4.8.2"
    assert corr_result["lead_deployment"]["service"] == "cart-service"
    assert corr_result["trace_metrics"]["slow_spans_count"] >= 1
    assert corr_result["trace_metrics"]["error_spans_count"] >= 1

    # Verify strict non-causal synthesis
    synthesis = corr_result["non_causal_synthesis"]
    assert "preceded the observed degradation" in synthesis
    assert "temporally aligned evidence" in synthesis
    assert "v4.8.2" in synthesis

    # Attach evidence items
    attached = CrossSourceCorrelator.attach_trace_evidence(db_session, incident.id)
    assert len(attached) >= 3

    # Check evidence types in attached records
    source_types = [ev.source_type for ev in attached]
    assert EvidenceSourceType.DEPLOYMENT in source_types
    assert EvidenceSourceType.CROSS_SOURCE_CORRELATION in source_types
    assert (
        EvidenceSourceType.CRITICAL_PATH in source_types
        or EvidenceSourceType.TRACE_ERROR_PATTERN in source_types
    )
