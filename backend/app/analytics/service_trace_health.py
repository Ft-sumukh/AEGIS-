"""Service Trace Health Snapshot Engine."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.service_dependencies import _percentile
from app.models.trace import TraceSpan
from app.telemetry.trace_schemas import ServiceTraceHealthResponse


class ServiceTraceHealthAnalyzer:
    """Calculates granular service-level health metrics derived from distributed trace spans."""

    @classmethod
    def get_health(
        cls,
        db: Session,
        service_name: str,
        environment: Optional[str] = "production",
        time_window_hours: int = 6,
        slow_threshold_ms: float = 500.0,
    ) -> ServiceTraceHealthResponse:
        """Computes comprehensive health indicators for a service from trace data."""
        window_start = datetime.now(UTC) - timedelta(hours=time_window_hours)

        q = select(TraceSpan).where(
            TraceSpan.service_name == service_name,
            TraceSpan.timestamp_start >= window_start,
        )
        if environment:
            q = q.where(TraceSpan.environment == environment)

        spans = db.scalars(q.order_by(TraceSpan.timestamp_start.asc())).all()

        if not spans:
            return ServiceTraceHealthResponse(
                service_name=service_name,
                environment=environment or "production",
                request_count=0,
                error_count=0,
                error_rate=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                slow_request_count=0,
                slow_request_percent=0.0,
                dependency_failures=0,
                trace_anomaly_count=0,
                health_status="HEALTHY",
            )

        req_count = len(spans)
        durations = [s.duration_ms for s in spans]
        error_count = sum(
            1 for s in spans if s.status == "ERROR" or (s.http_status_code and s.http_status_code >= 500)
        )
        error_rate = round(error_count / req_count, 4)

        p50 = _percentile(durations, 50)
        p95 = _percentile(durations, 95)
        p99 = _percentile(durations, 99)

        slow_count = sum(1 for d in durations if d >= slow_threshold_ms)
        slow_pct = round((slow_count / req_count) * 100.0, 1)

        # Count downstream dependency failures: child spans of this service that failed
        span_ids = {s.span_id for s in spans}
        child_spans = db.scalars(
            select(TraceSpan).where(
                TraceSpan.parent_span_id.in_(span_ids),
                TraceSpan.service_name != service_name,
                TraceSpan.timestamp_start >= window_start,
            )
        ).all()
        dep_failures = sum(
            1 for c in child_spans if c.status == "ERROR" or (c.http_status_code and c.http_status_code >= 500)
        )

        anomaly_count = 0
        if error_rate > 0.05:
            anomaly_count += 1
        if p95 > slow_threshold_ms:
            anomaly_count += 1
        if dep_failures > 5:
            anomaly_count += 1

        health_status = "HEALTHY"
        if error_rate >= 0.05 or slow_pct >= 20.0 or dep_failures > 0:
            health_status = "DEGRADED"
        if error_rate >= 0.20 or (req_count > 10 and error_count > 5 and p95 > 2000):
            health_status = "FAILED"

        return ServiceTraceHealthResponse(
            service_name=service_name,
            environment=environment or "production",
            request_count=req_count,
            error_count=error_count,
            error_rate=error_rate,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            slow_request_count=slow_count,
            slow_request_percent=slow_pct,
            dependency_failures=dep_failures,
            trace_anomaly_count=anomaly_count,
            health_status=health_status,
        )
