"""Operational metrics API endpoints."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.metrics import OperationalMetricRead
from app.services.metrics_service import MetricsService

logger = get_logger("aegis.api.metrics")
router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "",
    response_model=PaginatedResponse[OperationalMetricRead],
    status_code=status.HTTP_200_OK,
    summary="List operational metrics",
    description="Retrieve paginated time-series telemetry metrics with optional company and metric filters.",
)
def list_metrics(
    company_id: uuid.UUID | None = Query(default=None, description="Filter by company UUID"),
    metric_name: str | None = Query(default=None, description="Filter by metric name"),
    start_time: datetime.datetime | None = Query(default=None, description="Start timestamp (UTC)"),
    end_time: datetime.datetime | None = Query(default=None, description="End timestamp (UTC)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return (max 200)"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[OperationalMetricRead]:
    """List operational metrics with pagination."""
    try:
        items, total = MetricsService.list_metrics(
            db=db,
            company_id=company_id,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return PaginatedResponse(
            items=[OperationalMetricRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception(f"Error querying metrics: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving operational metrics.",
        ) from exc
