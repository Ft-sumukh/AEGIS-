"""Service Topology and Trace Health Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics.service_dependencies import ServiceDependencyAnalyzer
from app.analytics.service_trace_health import ServiceTraceHealthAnalyzer
from app.database.session import get_db
from app.telemetry.trace_schemas import (
    ServiceDependencyGraphResponse,
    ServiceTraceHealthResponse,
)

router = APIRouter(prefix="/services", tags=["Service Dependencies & Health"])


@router.get(
    "/dependencies",
    response_model=ServiceDependencyGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get service dependency graph",
    description="Discovers directed service topology from distributed trace parent-child boundaries.",
)
def get_service_dependencies(
    environment: Optional[str] = Query(default="production", description="Environment filter"),
    time_window_hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
    service: Optional[str] = Query(default=None, description="Filter for specific service"),
    db: Session = Depends(get_db),
) -> ServiceDependencyGraphResponse:
    return ServiceDependencyAnalyzer.get_dependency_graph(
        db=db,
        environment=environment,
        time_window_hours=time_window_hours,
        service_filter=service,
    )


@router.get(
    "/{service}/trace-health",
    response_model=ServiceTraceHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get service trace health snapshot",
    description="Calculates error rate, p95 latency, slow request %, and dependency failures for a service.",
)
def get_service_trace_health(
    service: str,
    environment: Optional[str] = Query(default="production", description="Environment"),
    time_window_hours: int = Query(default=6, ge=1, le=72, description="Time window in hours"),
    db: Session = Depends(get_db),
) -> ServiceTraceHealthResponse:
    return ServiceTraceHealthAnalyzer.get_health(
        db=db,
        service_name=service,
        environment=environment,
        time_window_hours=time_window_hours,
    )
