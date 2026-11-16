"""Service Dependency Discovery and Graph Analytics Engine."""

import math
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trace import TraceSpan
from app.telemetry.trace_schemas import (
    ServiceDependencyGraphResponse,
    ServiceDependencyItem,
)


def _percentile(values: list[float], pct: float) -> float:
    """Calculates percentile from list of floats."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(math.ceil((pct / 100.0) * len(sorted_vals))) - 1
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return round(sorted_vals[idx], 2)


class ServiceDependencyAnalyzer:
    """Derives caller -> callee service dependency metrics from distributed traces."""

    @classmethod
    def get_dependency_graph(
        cls,
        db: Session,
        environment: Optional[str] = "production",
        time_window_hours: int = 24,
        service_filter: Optional[str] = None,
    ) -> ServiceDependencyGraphResponse:
        """Discovers directed service dependencies by analyzing parent-child span boundaries."""
        window_start = datetime.now(UTC) - timedelta(hours=time_window_hours)

        query = select(TraceSpan).where(TraceSpan.timestamp_start >= window_start)
        if environment:
            query = query.where(TraceSpan.environment == environment)

        spans = db.scalars(query.order_by(TraceSpan.timestamp_start.asc())).all()

        # Build lookup table by span_id
        span_map: dict[str, TraceSpan] = {s.span_id: s for s in spans}

        # Mapping: (source_service, target_service, env) -> metrics dict
        dep_map: dict[tuple[str, str, str], dict[str, Any]] = {}

        for span in spans:
            source_svc: Optional[str] = None
            target_svc: str = span.service_name
            env = span.environment

            # Case A: Span has a parent span in the same trace with a DIFFERENT service name
            if span.parent_span_id and span.parent_span_id in span_map:
                parent = span_map[span.parent_span_id]
                if parent.service_name != target_svc:
                    source_svc = parent.service_name

            # Case B: Span specifies peer_service as a client call
            elif span.peer_service and span.peer_service != target_svc:
                source_svc = target_svc
                target_svc = span.peer_service

            if not source_svc or source_svc == target_svc:
                continue

            if service_filter and source_svc != service_filter and target_svc != service_filter:
                continue

            key = (source_svc, target_svc, env)
            if key not in dep_map:
                dep_map[key] = {
                    "source_service": source_svc,
                    "target_service": target_svc,
                    "environment": env,
                    "request_count": 0,
                    "error_count": 0,
                    "durations": [],
                    "first_seen": span.timestamp_start,
                    "last_seen": span.timestamp_start,
                }

            entry = dep_map[key]
            entry["request_count"] += 1
            if span.status == "ERROR" or (span.http_status_code and span.http_status_code >= 500):
                entry["error_count"] += 1
            entry["durations"].append(span.duration_ms)
            if span.timestamp_start < entry["first_seen"]:
                entry["first_seen"] = span.timestamp_start
            if span.timestamp_start > entry["last_seen"]:
                entry["last_seen"] = span.timestamp_start

        # Assemble Edges
        edges: list[ServiceDependencyItem] = []
        node_stats: dict[str, dict[str, Any]] = {}

        for entry in dep_map.values():
            req_cnt = entry["request_count"]
            err_cnt = entry["error_count"]
            err_rate = round(err_cnt / req_cnt, 4) if req_cnt > 0 else 0.0
            durations = entry["durations"]

            p50 = _percentile(durations, 50)
            p95 = _percentile(durations, 95)
            p99 = _percentile(durations, 99)

            item = ServiceDependencyItem(
                source_service=entry["source_service"],
                target_service=entry["target_service"],
                environment=entry["environment"],
                request_count=req_cnt,
                error_count=err_cnt,
                error_rate=err_rate,
                p50_latency_ms=p50,
                p95_latency_ms=p95,
                p99_latency_ms=p99,
                first_seen=entry["first_seen"],
                last_seen=entry["last_seen"],
            )
            edges.append(item)

            # Node aggregation
            for svc in (entry["source_service"], entry["target_service"]):
                if svc not in node_stats:
                    node_stats[svc] = {"requests": 0, "errors": 0, "durations": []}
                node_stats[svc]["requests"] += req_cnt
                node_stats[svc]["errors"] += err_cnt
                node_stats[svc]["durations"].extend(durations)

        # Assemble Nodes
        nodes: list[dict[str, Any]] = []
        for svc_name, s_data in node_stats.items():
            s_reqs = s_data["requests"]
            s_errs = s_data["errors"]
            s_err_rate = round(s_errs / s_reqs, 4) if s_reqs > 0 else 0.0
            s_p95 = _percentile(s_data["durations"], 95)

            health = "HEALTHY"
            if s_err_rate > 0.05 or s_p95 > 1000:
                health = "DEGRADED"
            if s_err_rate > 0.25:
                health = "FAILED"

            nodes.append(
                {
                    "service": svc_name,
                    "request_count": s_reqs,
                    "error_count": s_errs,
                    "error_rate": s_err_rate,
                    "p95_latency_ms": s_p95,
                    "health_status": health,
                }
            )

        return ServiceDependencyGraphResponse(
            nodes=nodes,
            edges=edges,
            time_window_start=window_start,
            time_window_end=datetime.now(UTC),
        )
