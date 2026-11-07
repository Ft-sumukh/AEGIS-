"""Pydantic schemas for AuditLog inspection."""

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditActorType


class AuditLogRead(BaseModel):
    """Sanitized, append-only security and operational audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    actor_type: AuditActorType
    actor_id: str
    action: str
    resource_type: str
    resource_id: str | None
    timestamp: datetime
    request_id: str | None
    audit_metadata: dict[str, Any]
