"""Trace Analytics and Reconstruction Service."""

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.critical_path import CriticalPathAnalyzer
from app.analytics.error_propagation import ErrorPropagationAnalyzer
from app.core.logging import get_logger
from app.models.trace import TraceSpan
from app.telemetry.trace_schemas import (
    TraceSpanNode,
    TraceSummaryItem,
    TraceTreeResponse,
)

logger = get_logger("aegis.analytics.trace_service")


class TraceService:
    """Reconstructs hierarchical trace trees and provides trace exploration capabilities."""

    @classmethod
    def get_trace(cls, db: Session, trace_id: str) -> Optional[TraceTreeResponse]:
        """Retrieves and reconstructs full trace tree without N+1 queries."""
        spans = db.scalars(
            select(TraceSpan)
            .where(TraceSpan.trace_id == trace_id)
            .order_by(TraceSpan.timestamp_start.asc())
        ).all()

        if not spans:
            return None

        # 1. Overall trace timing
        earliest_start = min(s.timestamp_start for s in spans)
        latest_end = max(s.timestamp_end for s in spans)
        total_duration = max(0.1, (latest_end - earliest_start).total_seconds() * 1000.0)

        # 2. Build nodes dictionary
        nodes_dict: dict[str, TraceSpanNode] = {}
        children_ids_map: dict[str, list[str]] = {}

        for s in spans:
            offset_ms = max(0.0, (s.timestamp_start - earliest_start).total_seconds() * 1000.0)
            node = TraceSpanNode(
                id=str(s.id),
                trace_id=s.trace_id,
                span_id=s.span_id,
                parent_span_id=s.parent_span_id,
                service_name=s.service_name,
                service_version=s.service_version,
                environment=s.environment,
                operation_name=s.operation_name,
                span_kind=s.span_kind,
                status=s.status,
                status_message=s.status_message,
                timestamp_start=s.timestamp_start,
                timestamp_end=s.timestamp_end,
                duration_ms=s.duration_ms,
                self_time_ms=s.duration_ms,  # Will be adjusted once children are linked
                start_offset_ms=round(offset_ms, 2),
                http_method=s.http_method,
                http_route=s.http_route,
                http_status_code=s.http_status_code,
                peer_service=s.peer_service,
                host=s.host,
                sanitized_attributes=s.sanitized_attributes or {},
                children=[],
            )
            nodes_dict[s.span_id] = node
            p_id = s.parent_span_id or "ROOT"
            children_ids_map.setdefault(p_id, []).append(s.span_id)

        # 3. Assemble hierarchy and compute self_time
        root_nodes: list[TraceSpanNode] = []
        for s in spans:
            p_id = s.parent_span_id
            if p_id and p_id in nodes_dict and p_id != s.span_id:
                nodes_dict[p_id].children.append(nodes_dict[s.span_id])
            else:
                root_nodes.append(nodes_dict[s.span_id])

        # Adjust self_time for each node: duration minus child durations
        for node in nodes_dict.values():
            child_dur = sum(c.duration_ms for c in node.children)
            node.self_time_ms = max(0.0, round(node.duration_ms - child_dur, 2))

        # Root span resolution
        root_node = root_nodes[0] if root_nodes else next(iter(nodes_dict.values()))
        if len(root_nodes) > 1 and root_node != root_nodes[0]:
            # Attach siblings if multiple top-level spans exist
            root_node.children.extend(root_nodes[1:])

        # 4. Critical Path & Error Propagation Analysis
        critical_path_res = CriticalPathAnalyzer.analyze(list(spans))
        error_prop_res = ErrorPropagationAnalyzer.analyze(list(spans))

        # 5. Distinct Services and Error Count
        distinct_services = sorted({s.service_name for s in spans})
        error_count = sum(1 for s in spans if s.status == "ERROR" or (s.http_status_code and s.http_status_code >= 500))
        overall_status = "ERROR" if error_count > 0 else "OK"

        return TraceTreeResponse(
            trace_id=trace_id,
            root_span=root_node,
            spans_count=len(spans),
            total_duration_ms=round(total_duration, 2),
            services=distinct_services,
            status=overall_status,
            error_count=error_count,
            critical_path=critical_path_res,
            error_propagation=error_prop_res,
        )

    @classmethod
    def list_traces(
        cls,
        db: Session,
        service: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        min_duration_ms: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TraceSummaryItem], int]:
        """Lists and filters aggregated trace summaries."""
        # Find matching trace_ids
        base_q = select(TraceSpan.trace_id).distinct()

        if service:
            base_q = base_q.where(TraceSpan.service_name == service)
        if environment:
            base_q = base_q.where(TraceSpan.environment == environment)
        if status:
            base_q = base_q.where(TraceSpan.status == status)
        if min_duration_ms is not None:
            base_q = base_q.where(TraceSpan.duration_ms >= min_duration_ms)
        if start_time:
            base_q = base_q.where(TraceSpan.timestamp_start >= start_time)
        if end_time:
            base_q = base_q.where(TraceSpan.timestamp_start <= end_time)

        # Count total matching traces
        count_q = select(func.count(func.distinct(TraceSpan.trace_id)))
        if service:
            count_q = count_q.where(TraceSpan.service_name == service)
        if environment:
            count_q = count_q.where(TraceSpan.environment == environment)
        if status:
            count_q = count_q.where(TraceSpan.status == status)
        if min_duration_ms is not None:
            count_q = count_q.where(TraceSpan.duration_ms >= min_duration_ms)
        if start_time:
            count_q = count_q.where(TraceSpan.timestamp_start >= start_time)
        if end_time:
            count_q = count_q.where(TraceSpan.timestamp_start <= end_time)

        total = db.scalar(count_q) or 0

        # Paginate trace_ids
        trace_ids = db.scalars(base_q.limit(limit).offset(offset)).all()
        if not trace_ids:
            return [], 0

        # Fetch all spans for these trace_ids
        spans = db.scalars(
            select(TraceSpan).where(TraceSpan.trace_id.in_(trace_ids)).order_by(TraceSpan.timestamp_start.asc())
        ).all()

        # Group spans by trace_id
        grouped: dict[str, list[TraceSpan]] = {}
        for s in spans:
            grouped.setdefault(s.trace_id, []).append(s)

        items: list[TraceSummaryItem] = []
        for t_id in trace_ids:
            t_spans = grouped.get(t_id, [])
            if not t_spans:
                continue

            earliest = min(s.timestamp_start for s in t_spans)
            latest = max(s.timestamp_end for s in t_spans)
            dur = max(0.1, (latest - earliest).total_seconds() * 1000.0)

            # Find root span: parent_span_id is None or parent not in trace spans
            all_ids = {s.span_id for s in t_spans}
            root_cands = [s for s in t_spans if not s.parent_span_id or s.parent_span_id not in all_ids]
            root = root_cands[0] if root_cands else t_spans[0]

            errors = sum(1 for s in t_spans if s.status == "ERROR" or (s.http_status_code and s.http_status_code >= 500))
            distinct_svcs = sorted({s.service_name for s in t_spans})

            items.append(
                TraceSummaryItem(
                    trace_id=t_id,
                    timestamp_start=earliest,
                    duration_ms=round(dur, 2),
                    root_service=root.service_name,
                    root_operation=root.operation_name,
                    status="ERROR" if errors > 0 else "OK",
                    span_count=len(t_spans),
                    error_count=errors,
                    services=distinct_svcs,
                    environment=root.environment,
                )
            )

        # Sort summary items by timestamp descending
        items.sort(key=lambda x: x.timestamp_start, reverse=True)
        return items, total

    @classmethod
    def get_slow_traces(
        cls,
        db: Session,
        min_duration_ms: float = 500.0,
        service: Optional[str] = None,
        limit: int = 20,
    ) -> list[TraceSummaryItem]:
        """Retrieves top slowest traces."""
        items, _ = cls.list_traces(
            db=db,
            service=service,
            min_duration_ms=min_duration_ms,
            limit=limit,
        )
        items.sort(key=lambda x: x.duration_ms, reverse=True)
        return items[:limit]

    @classmethod
    def get_error_traces(
        cls,
        db: Session,
        service: Optional[str] = None,
        limit: int = 20,
    ) -> list[TraceSummaryItem]:
        """Retrieves traces with failed spans."""
        items, _ = cls.list_traces(
            db=db,
            service=service,
            status="ERROR",
            limit=limit,
        )
        return items[:limit]
