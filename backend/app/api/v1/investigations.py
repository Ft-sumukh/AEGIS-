"""Investigation endpoints for triggering and inspecting AI operational diagnostics."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.database.session import get_db
from app.models.enums import InvestigationStatus
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.schemas.common import PaginatedResponse
from app.schemas.investigation import InvestigationRead
from app.security.auth import AuthUser, UserRole, require_role
from app.services.investigation_service import InvestigationService

logger = get_logger("aegis.api.investigations")
router = APIRouter(tags=["AI Investigations"])


@router.post(
    "/incidents/{incident_id}/investigate",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI investigation for incident",
    description="Initiates an automated diagnostic run using allowlisted tools and privacy redaction.",
)
def trigger_investigation(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(
        require_role([UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> InvestigationRead:
    """Launches an AI investigation under the authenticated user's authorization context."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    try:
        investigation, _findings = InvestigationService.start_investigation(
            db=db,
            incident_id=incident_id,
            actor=current_user.username,
        )
        db.commit()
        # Reload with eager relationships
        refreshed = InvestigationService.get_investigation_by_id(
            db=db, investigation_id=investigation.id
        )
        return InvestigationRead.model_validate(refreshed)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Investigation execution failed for incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete AI operational investigation.",
        ) from exc


@router.get(
    "/incidents/{incident_id}/investigations",
    response_model=list[InvestigationRead],
    status_code=status.HTTP_200_OK,
    summary="List investigations for an incident",
    description="Retrieves all historical diagnostic runs executed for this incident.",
)
def list_incident_investigations(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> list[InvestigationRead]:
    """Lists investigations for an incident."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    items = InvestigationService.list_investigations_for_incident(db=db, incident_id=incident_id)
    return [InvestigationRead.model_validate(inv) for inv in items]


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationRead,
    status_code=status.HTTP_200_OK,
    summary="Get investigation detail",
    description="Retrieves structured diagnostic findings, evaluated hypotheses, and mitigation recommendations.",
)
def get_investigation(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> InvestigationRead:
    """Retrieves detailed investigation findings."""
    investigation = InvestigationService.get_investigation_by_id(
        db=db, investigation_id=investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID {investigation_id} not found.",
        )

    return InvestigationRead.model_validate(investigation)


@router.get(
    "/investigations",
    response_model=PaginatedResponse[InvestigationRead],
    status_code=status.HTTP_200_OK,
    summary="List all AI investigations",
    description="Retrieves paginated operational diagnostics across incidents.",
)
def list_investigations(
    status_filter: InvestigationStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> PaginatedResponse[InvestigationRead]:
    """Lists investigations across all incidents with pagination."""
    query = select(Investigation).options(
        selectinload(Investigation.hypotheses),
        selectinload(Investigation.recommendations),
    )
    count_query = select(func.count(Investigation.id))

    if status_filter:
        query = query.where(Investigation.status == status_filter)
        count_query = count_query.where(Investigation.status == status_filter)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Investigation.started_at.desc()).limit(limit).offset(offset)
    ).all()

    return PaginatedResponse(
        items=[InvestigationRead.model_validate(inv) for inv in items],
        total=total,
        limit=limit,
        offset=offset,
    )
