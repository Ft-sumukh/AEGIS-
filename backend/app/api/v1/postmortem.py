"""Post-Mortem & Incident Retrospective API endpoints."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.incident import Incident
from app.security.auth import AuthUser, UserRole, require_role
from app.services.postmortem_service import PostMortemService

router = APIRouter(prefix="/incidents", tags=["Incident Post-Mortems"])


@router.post(
    "/{incident_id}/postmortem",
    summary="Generate automated AI Post-Mortem and Retrospective (PIR)",
)
def generate_incident_postmortem(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Generates an AI-synthesized Post-Incident Review with MTTD/MTTR analytics, 5 Whys, and action items."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    author = f"{user.username} (via Aegis AI)"
    postmortem = PostMortemService.generate_postmortem(db, incident, author=author)
    return postmortem


@router.get(
    "/{incident_id}/postmortem",
    summary="Get Post-Mortem report for an incident",
)
def get_incident_postmortem(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> dict[str, Any]:
    """Retrieves an existing Post-Mortem report or generates one on-demand if resolved."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    # Return cached postmortem if present
    cached = incident.incident_metadata.get("postmortem")
    if cached:
        return cached

    # Generate on-the-fly
    return PostMortemService.generate_postmortem(db, incident)


@router.get(
    "/{incident_id}/postmortem/markdown",
    summary="Export Post-Mortem report as Markdown",
)
def export_postmortem_markdown(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> Response:
    """Exports the Post-Incident Review as a downloadable GitHub-ready Markdown document."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    cached = incident.incident_metadata.get("postmortem")
    if not cached:
        cached = PostMortemService.generate_postmortem(db, incident)

    markdown_text = PostMortemService.render_markdown(cached)
    filename = f"postmortem_{str(incident.id)[:8]}.md"

    return Response(
        content=markdown_text,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
