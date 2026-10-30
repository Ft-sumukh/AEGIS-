"""Telemetry Ingestion and Exploration API Endpoints."""

import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.telemetry.schemas import (
    BatchTelemetryPayload,
    DataQualityMetrics,
    IngestionResult,
    SourceHealthStatus,
    TelemetryExploreItem,
    TelemetryExploreQuery,
)
from app.telemetry.service import TelemetryIngestionService
from app.telemetry.trace_schemas import BatchTracePayload, TraceIngestionResult

router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])
service = TelemetryIngestionService()


@router.post(
    "/events",
    response_model=IngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest batch operational telemetry",
    description="Ingests, sanitizes, normalizes, and stores operational metrics and system events.",
)
def ingest_telemetry_batch(
    payload: BatchTelemetryPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> IngestionResult:
    client_ip = request.client.host if request.client else "unknown_client"
    return service.ingest_batch(db, payload, client_key=client_ip)


@router.post(
    "/traces",
    response_model=TraceIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest batch distributed trace spans",
    description="Ingests, sanitizes, normalizes, and persists distributed trace spans with W3C context.",
)
def ingest_traces_batch(
    payload: BatchTracePayload,
    request: Request,
    db: Session = Depends(get_db),
) -> TraceIngestionResult:
    client_ip = request.client.host if request.client else "unknown_client"
    return service.ingest_traces(db, payload, client_key=client_ip)


@router.post(
    "/otel",
    response_model=IngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest OpenTelemetry OTLP JSON payload",
    description="Normalizes and ingests OTLP resourceMetrics, resourceLogs, and resourceSpans.",
)
def ingest_otel_payload(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> IngestionResult:
    client_ip = request.client.host if request.client else "unknown_client"
    return service.ingest_otel(db, payload, client_key=client_ip)


@router.get(
    "/sources",
    response_model=list[SourceHealthStatus],
    status_code=status.HTTP_200_OK,
    summary="Get telemetry sources health",
    description="Returns live throughput and connection health of registered telemetry sources.",
)
def get_sources_health(db: Session = Depends(get_db)) -> list[SourceHealthStatus]:
    return service.get_source_health(db)


@router.get(
    "/quality",
    response_model=DataQualityMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get telemetry data quality indicators",
    description="Calculates received, accepted, rejected, and deduplicated record counts.",
)
def get_data_quality(db: Session = Depends(get_db)) -> DataQualityMetrics:
    return service.get_quality_metrics(db)


@router.get(
    "/explore",
    response_model=list[TelemetryExploreItem],
    status_code=status.HTTP_200_OK,
    summary="Explore ingested operational telemetry",
    description="Unified time-series query across metrics and logs.",
)
def explore_telemetry(
    metric_name: Optional[str] = Query(default=None),
    service_name: Optional[str] = Query(default=None, alias="service"),
    environment: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[TelemetryExploreItem]:
    q = TelemetryExploreQuery(
        metric_name=metric_name,
        service=service_name,
        environment=environment,
        source=source,
        limit=limit,
    )
    return service.explore_telemetry(db, q)
