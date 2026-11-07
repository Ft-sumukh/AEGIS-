"""Pydantic schemas for Incident, IncidentEvidence, and IncidentNote entities."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.schemas.anomaly import AnomalyRead


class IncidentEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    source_type: EvidenceSourceType
    source_id: str | None = None
    title: str
    summary: str
    observed_at: datetime
    relevance_score: float
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IncidentEvidenceCreate(BaseModel):
    source_type: EvidenceSourceType
    source_id: str | None = None
    title: str = Field(..., max_length=255)
    summary: str
    observed_at: datetime
    relevance_override: float | None = None
    severity: SeverityLevel | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_level: str = "INTERNAL"


class IncidentNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    author: str
    text: str
    created_at: datetime


class IncidentNoteCreate(BaseModel):
    author: str = Field(..., max_length=100)
    text: str


class TimelineEventRead(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    title: str
    summary: str
    severity: SeverityLevel | None = None
    source_type: EvidenceSourceType | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentBase(BaseModel):
    company_id: uuid.UUID
    title: str = Field(..., max_length=255)
    summary: str
    severity: SeverityLevel
    severity_reason: str | None = None
    status: IncidentStatus = IncidentStatus.OPEN
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    affected_systems: list[str] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)

    detected_at: datetime
    investigation_started_at: datetime | None = None
    mitigated_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_by: str | None = None
    resolution_summary: str | None = None
    closed_by: str | None = None
    owner_id: str | None = None
    team_name: str | None = None

    recovery_status: str | None = None
    fingerprint: str | None = None

    confidence: float | None = None
    estimated_revenue_impact: Decimal | None = None
    estimated_orders_affected: int | None = None
    estimated_users_affected: int | None = None
    estimated_support_impact: int | None = None
    incident_metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentCreate(IncidentBase):
    pass


class IncidentCreateManual(BaseModel):
    company_id: uuid.UUID
    title: str = Field(..., max_length=255)
    summary: str
    severity: SeverityLevel = SeverityLevel.MEDIUM
    category: str | None = None
    affected_systems: list[str] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    detected_at: datetime | None = None
    owner_id: str | None = None
    team_name: str | None = None
    initial_note: str | None = None


class IncidentFromCandidateRequest(BaseModel):
    candidate_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    preliminary_summary: str
    severity: SeverityLevel
    correlation_score: float
    first_detected_at: datetime
    last_detected_at: datetime
    affected_metrics: list[str]
    anomaly_ids: list[uuid.UUID] = Field(default_factory=list)
    estimated_revenue_impact: float = 0.0
    estimated_orders_affected: int = 0
    estimated_users_affected: int = 0
    additional_support_tickets: int = 0
    additional_complaints: int = 0


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    reason: str | None = None
    resolution_summary: str | None = None
    closed_by: str | None = None


class IncidentAcknowledgeRequest(BaseModel):
    transition_to_investigating: bool = False


class IncidentImpactUpdateRequest(BaseModel):
    revenue_impact: float | None = None
    orders_affected: int | None = None
    users_affected: int | None = None
    support_impact: int | None = None


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class IncidentDetailRead(IncidentRead):
    model_config = ConfigDict(from_attributes=True)

    anomalies: list[AnomalyRead] = Field(default_factory=list)
    evidence: list[IncidentEvidenceRead] = Field(default_factory=list)
    notes: list[IncidentNoteRead] = Field(default_factory=list)


class IncidentCorrelationView(BaseModel):
    incident_id: uuid.UUID
    correlation_score: float | None = None
    candidate_id: str | None = None
    anomaly_count: int
    evidence_count: int
    affected_metrics: list[str]
    affected_systems: list[str]
    estimated_revenue_impact: float
    estimated_orders_affected: int
