"""Anomalies API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database.session import get_db
from app.models.enums import AnomalyStatus, SeverityLevel
from app.schemas.anomaly import AnomalyRead, AnomalySummary
from app.schemas.common import PaginatedResponse
from app.services.anomaly_service import AnomalyService

logger = get_logger("aegis.api.anomalies")
router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get(
    "/summary",
    response_model=AnomalySummary,
    status_code=status.HTTP_200_OK,
    summary="Get anomaly statistical summary",
    description="Retrieve aggregated anomaly statistics including counts by severity, status, detector type, and top affected metrics.",
)
def get_anomaly_summary(
    company_id: uuid.UUID | None = Query(
        default=None, description="Filter summary by company UUID"
    ),
    db: Session = Depends(get_db),
) -> AnomalySummary:
    """Retrieve anomaly aggregated summary metrics."""
    try:
        summary_data = AnomalyService.get_summary(db=db, company_id=company_id)
        return AnomalySummary.model_validate(summary_data)
    except Exception as exc:
        logger.exception(f"Error generating anomaly summary: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing the anomaly summary.",
        ) from exc


@router.get(
    "/{anomaly_id}",
    response_model=AnomalyRead,
    status_code=status.HTTP_200_OK,
    summary="Get anomaly details by ID",
    description="Retrieve full details for a single detected anomaly record.",
)
def get_anomaly_by_id(
    anomaly_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AnomalyRead:
    """Retrieve an anomaly by its unique identifier."""
    anomaly = AnomalyService.get_by_id(db=db, anomaly_id=anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly '{anomaly_id}' not found.",
        )
    return AnomalyRead.model_validate(anomaly)


@router.get(
    "",
    response_model=PaginatedResponse[AnomalyRead],
    status_code=status.HTTP_200_OK,
    summary="List detected anomalies",
    description="Retrieve paginated anomaly observations with optional company, severity, and status filtering.",
)
def list_anomalies(
    company_id: uuid.UUID | None = Query(default=None, description="Filter by company UUID"),
    severity: SeverityLevel | None = Query(default=None, description="Filter by severity level"),
    status_filter: AnomalyStatus | None = Query(
        default=None, alias="status", description="Filter by anomaly status"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return (max 200)"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AnomalyRead]:
    """List anomalies with pagination."""
    try:
        items, total = AnomalyService.list_anomalies(
            db=db,
            company_id=company_id,
            severity=severity,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
        return PaginatedResponse(
            items=[AnomalyRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception(f"Error querying anomalies: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving detected anomalies.",
        ) from exc
