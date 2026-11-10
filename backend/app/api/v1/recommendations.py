"""Recommendations API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database.session import get_db
from app.models.enums import RecommendationStatus, TicketPriority
from app.models.recommendation import Recommendation
from app.schemas.common import PaginatedResponse
from app.schemas.recommendation import RecommendationRead
from app.security.auth import AuthUser, UserRole, require_role

logger = get_logger("aegis.api.recommendations")
router = APIRouter(prefix="/recommendations", tags=["AI Recommendations"])


@router.get(
    "",
    response_model=PaginatedResponse[RecommendationRead],
    status_code=status.HTTP_200_OK,
    summary="List operational recommendations",
    description="Retrieves AI-formulated mitigation plans and recommendations across operational incidents.",
)
def list_recommendations(
    incident_id: uuid.UUID | None = Query(default=None, description="Filter by incident UUID"),
    status_filter: RecommendationStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    priority: TicketPriority | None = Query(default=None, description="Filter by priority"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> PaginatedResponse[RecommendationRead]:
    """Lists recommendations across incidents with pagination."""
    try:
        query = select(Recommendation)
        count_query = select(func.count(Recommendation.id))

        if incident_id:
            query = query.where(Recommendation.incident_id == incident_id)
            count_query = count_query.where(Recommendation.incident_id == incident_id)
        if status_filter:
            query = query.where(Recommendation.status == status_filter)
            count_query = count_query.where(Recommendation.status == status_filter)
        if priority:
            query = query.where(Recommendation.priority == priority)
            count_query = count_query.where(Recommendation.priority == priority)

        total = db.scalar(count_query) or 0
        items = db.scalars(
            query.order_by(Recommendation.created_at.desc()).limit(limit).offset(offset)
        ).all()

        return PaginatedResponse(
            items=[RecommendationRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception(f"Error querying recommendations: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve operational recommendations.",
        ) from exc
