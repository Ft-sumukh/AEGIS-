"""Incident Commander AI Co-Pilot API router."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.copilot.service import CoPilotService
from app.database.session import get_db
from app.security.auth import AuthUser, UserRole, require_role

router = APIRouter(prefix="/copilot", tags=["Incident Commander AI Co-Pilot"])


class CoPilotQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    incident_id: uuid.UUID | None = None
    context_hint: str | None = None


@router.post("/chat", summary="Query the Incident Commander AI Co-Pilot")
def chat_copilot(
    payload: CoPilotQueryRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> dict[str, Any]:
    """Provides conversational SRE context, announcement drafting, root cause explanations, and runbook matching."""
    return CoPilotService.query(
        db=db,
        message=payload.message,
        incident_id=payload.incident_id,
        context_hint=payload.context_hint,
    )
