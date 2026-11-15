"""SRE Runbooks and Operational Playbooks API router."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.incident import Incident
from app.runbooks.service import RunbookService
from app.security.auth import AuthUser, UserRole, require_role

router = APIRouter(prefix="/runbooks", tags=["SRE Runbooks & Playbooks"])


@router.get("", summary="List all operational runbooks")
def list_runbooks(
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Returns the full catalog of SRE standard operating runbooks."""
    return RunbookService.list_runbooks()


@router.get("/{runbook_id}", summary="Get runbook details by ID")
def get_runbook(
    runbook_id: str,
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> dict[str, Any]:
    """Retrieves a specific runbook by ID."""
    rb = RunbookService.get_runbook(runbook_id)
    if not rb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runbook '{runbook_id}' not found.",
        )
    return rb


@router.get("/for-incident/{incident_id}", summary="Match runbooks for an incident")
def match_runbooks_for_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Deterministically matches relevant playbooks for an active incident."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    return RunbookService.match_for_incident(incident)
