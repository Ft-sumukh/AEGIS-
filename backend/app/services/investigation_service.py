"""Service layer managing operational AI investigations lifecycle."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.investigator import AIInvestigator
from app.agents.schemas import StructuredInvestigationOutput
from app.core.logging import get_logger
from app.models.investigation import Investigation

logger = get_logger("aegis.services.investigation")


class InvestigationService:
    """Service layer managing diagnostic investigation runs and findings retrieval."""

    @staticmethod
    def start_investigation(
        db: Session,
        incident_id: uuid.UUID,
        actor: str = "analyst",
        request_id: str | None = None,
    ) -> tuple[Investigation, StructuredInvestigationOutput]:
        """Launches an automated AI investigation for an operational incident."""
        investigator = AIInvestigator()
        investigation, findings = investigator.investigate(
            db=db, incident_id=incident_id, actor_id=actor, request_id=request_id
        )
        return investigation, findings

    @staticmethod
    def get_investigation_by_id(
        db: Session, investigation_id: uuid.UUID
    ) -> Investigation | None:
        """Retrieves an investigation by UUID with eager loaded hypotheses and recommendations."""
        query = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .options(
                selectinload(Investigation.hypotheses),
                selectinload(Investigation.recommendations),
            )
        )
        return db.scalar(query)

    @staticmethod
    def list_investigations_for_incident(
        db: Session, incident_id: uuid.UUID
    ) -> list[Investigation]:
        """Lists all historical investigations executed for a given incident."""
        query = (
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .order_by(Investigation.started_at.desc())
            .options(
                selectinload(Investigation.hypotheses),
                selectinload(Investigation.recommendations),
            )
        )
        return list(db.scalars(query).all())
