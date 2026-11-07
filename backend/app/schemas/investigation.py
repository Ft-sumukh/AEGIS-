"""Pydantic schemas for Investigation and InvestigationHypothesis entities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HypothesisStatus, InvestigationStatus


from app.schemas.recommendation import RecommendationRead


class InvestigationHypothesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    title: str
    description: str
    status: HypothesisStatus
    confidence: float
    supporting_evidence_summary: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    status: InvestigationStatus
    started_at: datetime
    completed_at: datetime | None
    summary: str | None
    root_cause: str | None
    confidence: float | None
    uncertainty: float | None
    created_at: datetime
    updated_at: datetime
    hypotheses: list[InvestigationHypothesisRead] = Field(default_factory=list)
    recommendations: list[RecommendationRead] = Field(default_factory=list)
