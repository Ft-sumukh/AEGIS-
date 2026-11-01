"""Incidents API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database.session import get_db
from app.incidents.models import InvalidLifecycleTransitionError
from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.schemas.common import PaginatedResponse
from app.schemas.incident import (
    IncidentAcknowledgeRequest,
    IncidentCorrelationView,
    IncidentCreateManual,
    IncidentDetailRead,
    IncidentEvidenceCreate,
    IncidentEvidenceRead,
    IncidentFromCandidateRequest,
    IncidentImpactUpdateRequest,
    IncidentNoteCreate,
    IncidentNoteRead,
    IncidentRead,
    IncidentStatusUpdate,
    TimelineEventRead,
)
from app.security.auth import AuthUser, UserRole, require_role
from app.services.incident_service import IncidentService

logger = get_logger("aegis.api.incidents")
router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=PaginatedResponse[IncidentRead],
    status_code=status.HTTP_200_OK,
    summary="List operational incidents",
    description="Retrieve paginated incidents with company, severity, status, category, owner, and search filtering.",
)
def list_incidents(
    company_id: uuid.UUID | None = Query(default=None, description="Filter by company UUID"),
    severity: SeverityLevel | None = Query(default=None, description="Filter by severity level"),
    status_filter: IncidentStatus | None = Query(
        default=None, alias="status", description="Filter by incident status"
    ),
    category: str | None = Query(default=None, description="Filter by category"),
    owner_id: str | None = Query(default=None, description="Filter by owner identifier"),
    team_name: str | None = Query(default=None, description="Filter by team name"),
    search: str | None = Query(default=None, description="Search keyword in title or summary"),
    sort_by: str = Query(default="detected_at", description="Sort field"),
    sort_desc: bool = Query(default=True, description="Sort descending"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return (max 200)"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> PaginatedResponse[IncidentRead]:
    """List operational incidents with pagination."""
    try:
        items, total = IncidentService.list_incidents(
            db=db,
            company_id=company_id,
            severity=severity,
            status=status_filter,
            category=category,
            owner_id=owner_id,
            team_name=team_name,
            search=search,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
        )
        return PaginatedResponse(
            items=[IncidentRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception(f"Error querying incidents: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving operational incidents.",
        ) from exc


@router.post(
    "",
    response_model=IncidentDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual incident",
    description="Manually declare an operational incident by an authorized operator.",
)
def create_manual_incident(
    payload: IncidentCreateManual,
    actor: str = Query(default="operator", description="Operator username or system actor"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Manually creates an incident."""
    try:
        incident = IncidentService.create_manual(db=db, payload=payload, actor=actor)
        db.commit()
        refreshed = IncidentService.get_incident_by_id(db=db, incident_id=incident.id)
        return IncidentDetailRead.model_validate(refreshed)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error creating manual incident: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create manual incident.",
        ) from exc


@router.post(
    "/from-candidate",
    response_model=IncidentDetailRead,
    summary="Create or deduplicate incident from candidate",
    description="Transforms a deterministic analytics IncidentCandidate into an operational incident.",
)
def create_from_candidate(
    payload: IncidentFromCandidateRequest,
    response: Response,
    actor: str = Query(default="system", description="Actor creating the incident"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Transforms an IncidentCandidate into an Incident, handling deduplication."""
    try:
        incident, is_new = IncidentService.create_from_candidate(
            db=db, payload=payload, actor=actor
        )
        db.commit()
        response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        refreshed = IncidentService.get_incident_by_id(db=db, incident_id=incident.id)
        return IncidentDetailRead.model_validate(refreshed)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error creating incident from candidate: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create incident from candidate.",
        ) from exc


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get incident detail",
    description="Retrieve a single incident by UUID including associated anomalies, evidence, and notes.",
)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Retrieve detailed operational incident information."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    return IncidentDetailRead.model_validate(incident)


@router.post(
    "/{incident_id}/status",
    response_model=IncidentDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Update incident lifecycle status",
    description="Enforces valid state machine transitions (OPEN -> INVESTIGATING -> MITIGATED -> RESOLVED -> CLOSED).",
)
def update_incident_status(
    incident_id: uuid.UUID,
    payload: IncidentStatusUpdate,
    actor: str = Query(default="operator", description="Operator changing status"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Transitions an incident to a new lifecycle status."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        IncidentService.update_status(db=db, incident=incident, payload=payload, actor=actor)
        db.commit()
        refreshed = IncidentService.get_incident_by_id(db=db, incident_id=incident.id)
        return IncidentDetailRead.model_validate(refreshed)
    except InvalidLifecycleTransitionError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error updating status for incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update incident status.",
        ) from exc


@router.post(
    "/{incident_id}/acknowledge",
    response_model=IncidentDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge incident",
    description="Records operator acknowledgement and optionally transitions status to INVESTIGATING.",
)
def acknowledge_incident(
    incident_id: uuid.UUID,
    payload: IncidentAcknowledgeRequest,
    actor: str = Query(default="operator", description="Operator acknowledging incident"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Records operator acknowledgement."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        IncidentService.acknowledge_incident(db=db, incident=incident, payload=payload, actor=actor)
        db.commit()
        refreshed = IncidentService.get_incident_by_id(db=db, incident_id=incident.id)
        return IncidentDetailRead.model_validate(refreshed)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error acknowledging incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge incident.",
        ) from exc


@router.get(
    "/{incident_id}/timeline",
    response_model=list[TimelineEventRead],
    status_code=status.HTTP_200_OK,
    summary="Get incident chronological timeline",
    description="Aggregates multi-source events into an ordered timeline with privacy masking.",
)
def get_incident_timeline(
    incident_id: uuid.UUID,
    ascending: bool = Query(
        default=True, description="Chronological ordering (True=asc, False=desc)"
    ),
    include_adjacent: bool = Query(
        default=True, description="Include temporally adjacent system events"
    ),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> list[TimelineEventRead]:
    """Retrieves incident chronological timeline."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        events = IncidentService.get_timeline(
            db=db,
            incident=incident,
            ascending=ascending,
            include_adjacent=include_adjacent,
        )
        return [TimelineEventRead.model_validate(e) for e in events]
    except Exception as exc:
        logger.exception(f"Error generating timeline for incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate incident timeline.",
        ) from exc


@router.get(
    "/{incident_id}/evidence",
    response_model=list[IncidentEvidenceRead],
    status_code=status.HTTP_200_OK,
    summary="List incident evidence",
    description="Retrieves evidence items ordered by deterministic relevance score descending.",
)
def list_incident_evidence(
    incident_id: uuid.UUID,
    source_type: EvidenceSourceType | None = Query(
        default=None, description="Filter by source type"
    ),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> list[IncidentEvidenceRead]:
    """List attached evidence."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    items = IncidentService.list_evidence(db=db, incident_id=incident_id, source_type=source_type)
    return [IncidentEvidenceRead.model_validate(e) for e in items]


@router.post(
    "/{incident_id}/evidence",
    response_model=IncidentEvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add evidence to incident",
    description="Attaches a new evidence item with deterministic relevance scoring and deduplication.",
)
def add_incident_evidence(
    incident_id: uuid.UUID,
    payload: IncidentEvidenceCreate,
    actor: str = Query(default="operator", description="Actor attaching evidence"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentEvidenceRead:
    """Attaches an evidence record to an incident."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        ev = IncidentService.add_evidence(db=db, incident=incident, payload=payload, actor=actor)
        db.commit()
        db.refresh(ev)
        return IncidentEvidenceRead.model_validate(ev)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error attaching evidence to incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attach evidence to incident.",
        ) from exc


@router.get(
    "/{incident_id}/notes",
    response_model=list[IncidentNoteRead],
    status_code=status.HTTP_200_OK,
    summary="List operator notes",
    description="Retrieves chronological operator and system annotations.",
)
def list_incident_notes(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> list[IncidentNoteRead]:
    """Lists operator notes."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    notes = IncidentService.list_notes(db=db, incident_id=incident_id)
    return [IncidentNoteRead.model_validate(n) for n in notes]


@router.post(
    "/{incident_id}/notes",
    response_model=IncidentNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add note to incident",
    description="Appends a structured note from an operator or system actor.",
)
def add_incident_note(
    incident_id: uuid.UUID,
    payload: IncidentNoteCreate,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentNoteRead:
    """Adds a note to an incident."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        note = IncidentService.add_note(db=db, incident=incident, payload=payload)
        db.commit()
        db.refresh(note)
        return IncidentNoteRead.model_validate(note)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error adding note to incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add note to incident.",
        ) from exc


@router.post(
    "/{incident_id}/impact",
    response_model=IncidentDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Update incident impact estimation",
    description="Updates preliminary blast radius and appends impact history delta.",
)
def update_incident_impact(
    incident_id: uuid.UUID,
    payload: IncidentImpactUpdateRequest,
    actor: str = Query(default="operator", description="Actor updating impact"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentDetailRead:
    """Updates preliminary business impact."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    try:
        IncidentService.update_impact(db=db, incident=incident, payload=payload, actor=actor)
        db.commit()
        refreshed = IncidentService.get_incident_by_id(db=db, incident_id=incident.id)
        return IncidentDetailRead.model_validate(refreshed)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Error updating impact for incident {incident_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update incident impact.",
        ) from exc


@router.get(
    "/{incident_id}/correlation",
    response_model=IncidentCorrelationView,
    status_code=status.HTTP_200_OK,
    summary="Get incident correlation view",
    description="Returns high-level correlation summary and anomaly metrics overview.",
)
def get_incident_correlation(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> IncidentCorrelationView:
    """Returns correlation overview."""
    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    return IncidentService.get_correlation_view(incident)


@router.get(
    "/{incident_id}/traces",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get correlated trace evidence for incident",
    description="Retrieves cross-source correlation linking deployments, traces, logs, and metrics with non-causal evidence.",
)
def get_incident_traces(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])),
) -> dict:
    """Returns cross-source trace evidence for the incident."""
    from app.analytics.cross_correlation import CrossSourceCorrelator

    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    return CrossSourceCorrelator.correlate_incident(db, incident_id)


@router.post(
    "/{incident_id}/correlate-traces",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="Attach trace evidence to incident",
    description="Analyzes and persists trace, critical path, and error propagation evidence items to the incident.",
)
def attach_incident_trace_evidence(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
) -> list[dict]:
    """Generates and attaches trace evidence items."""
    from app.analytics.cross_correlation import CrossSourceCorrelator

    incident = IncidentService.get_incident_by_id(db=db, incident_id=incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} was not found.",
        )
    items = CrossSourceCorrelator.attach_trace_evidence(db, incident_id)
    return [
        {
            "id": str(i.id),
            "source_type": i.source_type.value,
            "title": i.title,
            "summary": i.summary,
            "relevance_score": i.relevance_score,
            "observed_at": i.observed_at.isoformat(),
        }
        for i in items
    ]

