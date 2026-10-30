"""Distributed Tracing API Endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.trace_service import TraceService
from app.database.session import get_db
from app.models.trace import TraceSpan
from app.telemetry.service import TelemetryIngestionService
from app.telemetry.trace_schemas import (
    BatchTracePayload,
    TraceIngestionResult,
    TraceSummaryItem,
    TraceTreeResponse,
)

router = APIRouter(prefix="/traces", tags=["Distributed Tracing"])
ingestion_service = TelemetryIngestionService()


@router.get(
    "",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Query distributed traces",
    description="Retrieves aggregated trace summaries matching service, environment, duration, and time filters.",
)
def list_traces(
    service: Optional[str] = Query(default=None, description="Service name filter"),
    environment: Optional[str] = Query(default=None, description="Environment filter"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Status filter: OK, ERROR"),
    min_duration_ms: Optional[float] = Query(default=None, description="Minimum trace latency in ms"),
    start_time: Optional[datetime] = Query(default=None, description="ISO start time"),
    end_time: Optional[datetime] = Query(default=None, description="ISO end time"),
    limit: int = Query(default=50, le=200, description="Max items per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> dict:
    items, total = TraceService.list_traces(
        db=db,
        service=service,
        environment=environment,
        status=status_filter,
        min_duration_ms=min_duration_ms,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [itm.model_dump() for itm in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/slow",
    response_model=list[TraceSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="Get slowest traces",
    description="Returns top slowest traces exceeding duration threshold.",
)
def get_slow_traces(
    min_duration_ms: float = Query(default=500.0, description="Minimum duration in ms"),
    service: Optional[str] = Query(default=None, description="Service filter"),
    limit: int = Query(default=20, le=100, description="Max traces"),
    db: Session = Depends(get_db),
) -> list[TraceSummaryItem]:
    return TraceService.get_slow_traces(
        db=db,
        min_duration_ms=min_duration_ms,
        service=service,
        limit=limit,
    )


@router.get(
    "/errors",
    response_model=list[TraceSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="Get failed traces",
    description="Returns traces containing failed spans or HTTP 5xx errors.",
)
def get_error_traces(
    service: Optional[str] = Query(default=None, description="Service filter"),
    limit: int = Query(default=20, le=100, description="Max traces"),
    db: Session = Depends(get_db),
) -> list[TraceSummaryItem]:
    return TraceService.get_error_traces(
        db=db,
        service=service,
        limit=limit,
    )


@router.get(
    "/{trace_id}",
    response_model=TraceTreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get trace hierarchy and analysis",
    description="Reconstructs complete span tree with critical path and error propagation analysis.",
)
def get_trace(
    trace_id: str,
    db: Session = Depends(get_db),
) -> TraceTreeResponse:
    trace_clean = trace_id.strip().lower().replace("0x", "")
    trace_res = TraceService.get_trace(db=db, trace_id=trace_clean)
    if not trace_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace '{trace_id}' not found.",
        )
    return trace_res


@router.get(
    "/{trace_id}/spans",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="Get flat span list for trace",
    description="Returns raw sanitized span records for a specific trace ID.",
)
def get_trace_spans(
    trace_id: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    trace_clean = trace_id.strip().lower().replace("0x", "")
    spans = db.scalars(
        select(TraceSpan)
        .where(TraceSpan.trace_id == trace_clean)
        .order_by(TraceSpan.timestamp_start.asc())
    ).all()

    if not spans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No spans found for trace '{trace_id}'.",
        )

    return [
        {
            "id": str(s.id),
            "trace_id": s.trace_id,
            "span_id": s.span_id,
            "parent_span_id": s.parent_span_id,
            "service_name": s.service_name,
            "operation_name": s.operation_name,
            "span_kind": s.span_kind,
            "status": s.status,
            "status_message": s.status_message,
            "duration_ms": s.duration_ms,
            "timestamp_start": s.timestamp_start.isoformat(),
            "timestamp_end": s.timestamp_end.isoformat(),
            "http_method": s.http_method,
            "http_route": s.http_route,
            "http_status_code": s.http_status_code,
            "sanitized_attributes": s.sanitized_attributes or {},
        }
        for s in spans
    ]
