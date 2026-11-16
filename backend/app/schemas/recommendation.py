"""Pydantic schemas for Recommendation entities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RecommendationStatus, SeverityLevel, TicketPriority


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    incident_id: uuid.UUID
    title: str
    description: str
    priority: TicketPriority
    risk_level: SeverityLevel
    expected_impact: str
    status: RecommendationStatus
    created_at: datetime
    updated_at: datetime
