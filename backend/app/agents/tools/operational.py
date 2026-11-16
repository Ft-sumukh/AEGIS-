"""Typed operational tools providing minimized data to the AI investigator."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident
from app.models.metrics import OperationalMetric
from app.models.support import CustomerComplaint, SupportTicket
from app.security.policy import InvestigationBudgetTracker
from app.security.pseudonymizer import pseudonymize_customer, pseudonymize_ticket
from app.security.sanitizer import DataSanitizer


def _parse_dt(val: str | datetime | None) -> datetime | None:
    """Safely normalizes string or datetime input to UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    if isinstance(val, str):
        cleaned = val.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def get_incident(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> dict[str, Any]:
    """Retrieves high-level metadata for an incident with data minimization."""
    inc_uuid = uuid.UUID(str(incident_id))
    incident = db.get(Incident, inc_uuid)
    if not incident:
        return {"error": f"Incident {incident_id} not found."}

    return {
        "incident_id": str(incident.id),
        "title": incident.title,
        "summary": incident.summary,
        "severity": incident.severity.value,
        "status": incident.status.value,
        "category": incident.category,
        "affected_systems": incident.affected_systems,
        "affected_metrics": incident.affected_metrics,
        "detected_at": incident.detected_at.isoformat(),
    }


def get_timeline(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> list[dict[str, Any]]:
    """Retrieves chronological timeline events for an incident."""
    inc_uuid = uuid.UUID(str(incident_id))
    incident = db.get(Incident, inc_uuid)
    if not incident:
        return []

    from app.services.incident_service import IncidentService

    events = IncidentService.get_timeline(db=db, incident=incident)
    max_records = budget_tracker.limits.max_records_per_tool_call

    minimized = []
    for e in events[:max_records]:
        minimized.append(
            {
                "timestamp": e.timestamp.isoformat(),
                "source": e.source.value if hasattr(e.source, "value") else str(e.source),
                "event_type": e.event_type,
                "title": e.title,
                "summary": e.summary,
                "severity": e.severity.value if hasattr(e.severity, "value") else str(e.severity),
            }
        )
    return minimized


def get_anomalies(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> list[dict[str, Any]]:
    """Retrieves correlated anomalies for an operational incident."""
    inc_uuid = uuid.UUID(str(incident_id))
    incident = db.get(Incident, inc_uuid)
    if not incident:
        return []

    max_records = budget_tracker.limits.max_records_per_tool_call
    anomalies = incident.anomalies[:max_records]

    return [
        {
            "anomaly_id": str(a.id),
            "metric_name": a.metric_name,
            "service_name": a.service_name,
            "score": a.score,
            "severity": a.severity.value,
            "detector_type": a.detector_type.value,
            "start_time": a.start_time.isoformat(),
            "end_time": a.end_time.isoformat(),
            "deviation": a.deviation,
            "actual_value": a.actual_value,
            "expected_value": a.expected_value,
        }
        for a in anomalies
    ]


def get_metric_window(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    metric_name: str,
    start_time: str | datetime,
    end_time: str | datetime,
    service_name: str | None = None,
) -> list[dict[str, Any]]:
    """Queries time-series telemetry data within bounded time window with data minimization."""
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if not st or not et:
        return [{"error": "Invalid start_time or end_time format."}]

    # Enforce time-window boundary
    budget_tracker.validate_time_window(st, et)
    max_records = budget_tracker.limits.max_records_per_tool_call

    query = (
        select(OperationalMetric)
        .where(
            OperationalMetric.metric_name == metric_name,
            OperationalMetric.timestamp >= st,
            OperationalMetric.timestamp <= et,
        )
        .order_by(OperationalMetric.timestamp.asc())
        .limit(max_records)
    )
    if service_name:
        query = query.where(OperationalMetric.service_name == service_name)

    records = db.scalars(query).all()
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "metric_name": r.metric_name,
            "service_name": r.service_name,
            "value": float(r.value),
            "unit": r.unit,
        }
        for r in records
    ]


def compare_metrics(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    metric_name: str,
    baseline_start: str | datetime,
    baseline_end: str | datetime,
    incident_start: str | datetime,
    incident_end: str | datetime,
    service_name: str | None = None,
) -> dict[str, Any]:
    """Computes statistical comparison between normal baseline and incident window."""
    b_st = _parse_dt(baseline_start)
    b_et = _parse_dt(baseline_end)
    i_st = _parse_dt(incident_start)
    i_et = _parse_dt(incident_end)

    if not b_st or not b_et or not i_st or not i_et:
        return {"error": "Invalid date parameters provided."}

    budget_tracker.validate_time_window(b_st, b_et)
    budget_tracker.validate_time_window(i_st, i_et)

    def _get_stats(st: datetime, et: datetime) -> tuple[float | None, float | None, int]:
        q = select(
            func.avg(OperationalMetric.value),
            func.max(OperationalMetric.value),
            func.count(OperationalMetric.id),
        ).where(
            OperationalMetric.metric_name == metric_name,
            OperationalMetric.timestamp >= st,
            OperationalMetric.timestamp <= et,
        )
        if service_name:
            q = q.where(OperationalMetric.service_name == service_name)
        row = db.execute(q).first()
        if row:
            avg_val = float(row[0]) if row[0] is not None else None
            max_val = float(row[1]) if row[1] is not None else None
            cnt = int(row[2]) if row[2] is not None else 0
            return avg_val, max_val, cnt
        return None, None, 0

    base_avg, base_max, base_count = _get_stats(b_st, b_et)
    inc_avg, inc_max, inc_count = _get_stats(i_st, i_et)

    delta_pct = None
    if base_avg is not None and inc_avg is not None and base_avg != 0:
        delta_pct = round(((inc_avg - base_avg) / abs(base_avg)) * 100.0, 2)

    return {
        "metric_name": metric_name,
        "service_name": service_name,
        "baseline": {"avg": base_avg, "max": base_max, "data_points": base_count},
        "incident": {"avg": inc_avg, "max": inc_max, "data_points": inc_count},
        "delta_percentage": delta_pct,
    }


def get_deployments(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    start_time: str | datetime,
    end_time: str | datetime,
    service_name: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves deployment events with secrets and credentials strictly removed."""
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if not st or not et:
        return []

    budget_tracker.validate_time_window(st, et)
    max_records = budget_tracker.limits.max_records_per_tool_call

    query = (
        select(Deployment)
        .where(Deployment.deployed_at >= st, Deployment.deployed_at <= et)
        .order_by(Deployment.deployed_at.desc())
        .limit(max_records)
    )
    if service_name:
        query = query.where(Deployment.service == service_name)

    deployments = db.scalars(query).all()
    # Data minimization: Never return raw metadata or repo credentials
    return [
        {
            "deployment_id": str(d.id),
            "service_name": d.service,
            "version": d.version,
            "status": d.status.value,
            "environment": d.environment,
            "started_at": d.deployed_at.isoformat(),
            "completed_at": d.deployed_at.isoformat(),
        }
        for d in deployments
    ]


def get_system_events(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    start_time: str | datetime,
    end_time: str | datetime,
    service_name: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves system operational events."""
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if not st or not et:
        return []

    budget_tracker.validate_time_window(st, et)
    max_records = budget_tracker.limits.max_records_per_tool_call

    query = (
        select(SystemEvent)
        .where(SystemEvent.timestamp >= st, SystemEvent.timestamp <= et)
        .order_by(SystemEvent.timestamp.desc())
        .limit(max_records)
    )
    if service_name:
        query = query.where(SystemEvent.service == service_name)

    events = db.scalars(query).all()
    return [
        {
            "event_id": str(e.id),
            "service_name": e.service,
            "event_type": e.event_type,
            "severity": e.severity.value,
            "summary": e.message,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]


def get_support_tickets(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    start_time: str | datetime,
    end_time: str | datetime,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves customer support tickets with customer identity pseudonymized and PII stripped."""
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if not st or not et:
        return []

    budget_tracker.validate_time_window(st, et)
    max_records = budget_tracker.limits.max_records_per_tool_call

    query = (
        select(SupportTicket)
        .where(SupportTicket.created_at >= st, SupportTicket.created_at <= et)
        .order_by(SupportTicket.created_at.desc())
        .limit(max_records)
    )
    if category:
        query = query.where(SupportTicket.category == category)

    tickets = db.scalars(query).all()
    # Data minimization: Strip requester email and phone, pseudonymize ticket ID
    return [
        {
            "ticket_reference": pseudonymize_ticket(str(t.id)),
            "category": t.category,
            "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "summary": DataSanitizer.sanitize_text(t.summary),
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]


def get_customer_complaints(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    start_time: str | datetime,
    end_time: str | datetime,
) -> list[dict[str, Any]]:
    """Retrieves customer complaints with customer IDs deterministically pseudonymized."""
    st = _parse_dt(start_time)
    et = _parse_dt(end_time)
    if not st or not et:
        return []

    budget_tracker.validate_time_window(st, et)
    max_records = budget_tracker.limits.max_records_per_tool_call

    query = (
        select(CustomerComplaint)
        .where(CustomerComplaint.created_at >= st, CustomerComplaint.created_at <= et)
        .order_by(CustomerComplaint.created_at.desc())
        .limit(max_records)
    )

    complaints = db.scalars(query).all()
    return [
        {
            "complaint_id": str(c.id),
            "customer_reference": pseudonymize_customer(str(c.customer_id)) if c.customer_id else None,
            "category": c.category,
            "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
            "summary": DataSanitizer.sanitize_text(c.summary),
            "created_at": c.created_at.isoformat(),
        }
        for c in complaints
    ]


def get_impact(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> dict[str, Any]:
    """Retrieves calculated business blast radius and customer impact."""
    inc_uuid = uuid.UUID(str(incident_id))
    incident = db.get(Incident, inc_uuid)
    if not incident:
        return {"error": f"Incident {incident_id} not found."}

    return {
        "incident_id": str(incident.id),
        "estimated_revenue_impact": float(incident.estimated_revenue_impact)
        if incident.estimated_revenue_impact
        else 0.0,
        "estimated_orders_affected": incident.estimated_orders_affected or 0,
        "estimated_users_affected": incident.estimated_users_affected or 0,
        "estimated_support_impact": incident.estimated_support_impact or 0,
    }


def get_related_incidents(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> list[dict[str, Any]]:
    """Retrieves historical incidents sharing affected systems or categories."""
    inc_uuid = uuid.UUID(str(incident_id))
    incident = db.get(Incident, inc_uuid)
    if not incident:
        return []

    max_records = 5
    query = (
        select(Incident)
        .where(
            Incident.id != inc_uuid,
            Incident.category == incident.category,
        )
        .order_by(Incident.detected_at.desc())
        .limit(max_records)
    )

    rel_incidents = db.scalars(query).all()
    return [
        {
            "incident_id": str(ri.id),
            "title": ri.title,
            "severity": ri.severity.value,
            "detected_at": ri.detected_at.isoformat(),
            "root_cause": ri.resolution_summary,
        }
        for ri in rel_incidents
    ]


# ==============================================================================
# Phase 2 Distributed Tracing & Observability Tools
# ==============================================================================


def get_trace(
    db: Session, budget_tracker: InvestigationBudgetTracker, trace_id: str
) -> dict[str, Any]:
    """Retrieves reconstructed trace execution tree with sanitized attributes."""
    from app.analytics.trace_service import TraceService

    trace_clean = str(trace_id).strip().lower().replace("0x", "")
    trace_res = TraceService.get_trace(db, trace_clean)
    if not trace_res:
        return {"error": f"Trace {trace_id} not found."}

    return DataSanitizer.sanitize_dict(trace_res.model_dump())


def get_trace_summary(
    db: Session, budget_tracker: InvestigationBudgetTracker, trace_id: str
) -> dict[str, Any]:
    """Retrieves concise executive summary of a trace without huge payloads."""
    from app.analytics.trace_service import TraceService

    trace_clean = str(trace_id).strip().lower().replace("0x", "")
    trace_res = TraceService.get_trace(db, trace_clean)
    if not trace_res:
        return {"error": f"Trace {trace_id} not found."}

    summary = {
        "trace_id": trace_res.trace_id,
        "total_duration_ms": trace_res.total_duration_ms,
        "spans_count": trace_res.spans_count,
        "services": trace_res.services,
        "status": trace_res.status,
        "error_count": trace_res.error_count,
        "root_service": trace_res.root_span.service_name if trace_res.root_span else "unknown",
        "root_operation": trace_res.root_span.operation_name if trace_res.root_span else "unknown",
        "critical_path_assessment": trace_res.critical_path.non_causal_assessment if trace_res.critical_path else None,
        "error_propagation_assessment": trace_res.error_propagation.non_causal_assessment if trace_res.error_propagation else None,
    }
    return DataSanitizer.sanitize_dict(summary)


def get_slow_traces(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    service_name: Optional[str] = None,
    limit: int = 10,
    min_duration_ms: float = 500.0,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieves slowest distributed traces matching time window and service filters."""
    from app.analytics.trace_service import TraceService

    st = _parse_dt(start_time) if start_time else None
    et = _parse_dt(end_time) if end_time else None
    if st and et:
        budget_tracker.validate_time_window(st, et)

    bounded_limit = min(limit, budget_tracker.limits.max_records_per_tool_call, 20)
    items, _ = TraceService.list_traces(
        db=db,
        service=service_name,
        min_duration_ms=min_duration_ms,
        start_time=st,
        end_time=et,
        limit=bounded_limit,
    )
    items.sort(key=lambda x: x.duration_ms, reverse=True)
    return [DataSanitizer.sanitize_dict(itm.model_dump()) for itm in items[:bounded_limit]]


def get_failed_traces(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    service_name: Optional[str] = None,
    limit: int = 10,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieves traces containing errors or HTTP 5xx failures."""
    from app.analytics.trace_service import TraceService

    st = _parse_dt(start_time) if start_time else None
    et = _parse_dt(end_time) if end_time else None
    if st and et:
        budget_tracker.validate_time_window(st, et)

    bounded_limit = min(limit, budget_tracker.limits.max_records_per_tool_call, 20)
    items = TraceService.get_error_traces(
        db=db,
        service=service_name,
        limit=bounded_limit,
    )
    return [DataSanitizer.sanitize_dict(itm.model_dump()) for itm in items]


def get_service_dependencies(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    service_name: Optional[str] = None,
    environment: Optional[str] = "production",
    time_window_hours: int = 24,
) -> dict[str, Any]:
    """Discovers directed caller -> callee service dependency metrics."""
    from app.analytics.service_dependencies import ServiceDependencyAnalyzer

    bounded_hours = min(max(1, time_window_hours), 72)
    graph = ServiceDependencyAnalyzer.get_dependency_graph(
        db=db,
        environment=environment,
        time_window_hours=bounded_hours,
        service_filter=service_name,
    )
    return DataSanitizer.sanitize_dict(graph.model_dump())


def get_service_trace_health(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    service_name: str,
    environment: Optional[str] = "production",
    time_window_hours: int = 6,
) -> dict[str, Any]:
    """Retrieves per-service health snapshot derived from traces."""
    from app.analytics.service_trace_health import ServiceTraceHealthAnalyzer

    bounded_hours = min(max(1, time_window_hours), 48)
    health = ServiceTraceHealthAnalyzer.get_health(
        db=db,
        service_name=service_name,
        environment=environment,
        time_window_hours=bounded_hours,
    )
    return DataSanitizer.sanitize_dict(health.model_dump())


def get_critical_path(
    db: Session, budget_tracker: InvestigationBudgetTracker, trace_id: str
) -> dict[str, Any]:
    """Calculates latency-determining critical path through trace graph."""
    from app.analytics.critical_path import CriticalPathAnalyzer
    from app.models.trace import TraceSpan

    trace_clean = str(trace_id).strip().lower().replace("0x", "")
    spans = db.scalars(
        select(TraceSpan).where(TraceSpan.trace_id == trace_clean)
    ).all()
    if not spans:
        return {"error": f"Trace {trace_id} not found."}

    cp = CriticalPathAnalyzer.analyze(list(spans))
    return DataSanitizer.sanitize_dict(cp.model_dump())


def get_trace_error_patterns(
    db: Session,
    budget_tracker: InvestigationBudgetTracker,
    service_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Analyzes error propagation sequences across failed traces."""
    from app.analytics.error_propagation import ErrorPropagationAnalyzer
    from app.analytics.trace_service import TraceService
    from app.models.trace import TraceSpan

    st = _parse_dt(start_time) if start_time else None
    et = _parse_dt(end_time) if end_time else None
    if st and et:
        budget_tracker.validate_time_window(st, et)

    error_trace_items = TraceService.get_error_traces(db=db, service=service_name, limit=5)
    patterns: list[dict[str, Any]] = []

    for itm in error_trace_items:
        spans = db.scalars(
            select(TraceSpan).where(TraceSpan.trace_id == itm.trace_id)
        ).all()
        if spans:
            ep = ErrorPropagationAnalyzer.analyze(list(spans))
            if ep.has_errors:
                patterns.append(DataSanitizer.sanitize_dict(ep.model_dump()))

    return patterns


def get_correlated_trace_evidence(
    db: Session, budget_tracker: InvestigationBudgetTracker, incident_id: str
) -> dict[str, Any]:
    """Retrieves structured cross-source correlation linking deployments, traces, logs, and business impact."""
    from app.analytics.cross_correlation import CrossSourceCorrelator

    inc_uuid = uuid.UUID(str(incident_id))
    corr = CrossSourceCorrelator.correlate_incident(db, inc_uuid)
    return DataSanitizer.sanitize_dict(corr)

