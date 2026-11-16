"""Pydantic schemas for Operations Intelligence analytics API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsRunRequest(BaseModel):
    """Request payload to trigger an analytics detection and correlation run."""

    company_id: uuid.UUID = Field(..., description="Target company UUID")
    start_time: datetime | None = Field(
        default=None, description="Optional start timestamp for analysis window"
    )
    end_time: datetime | None = Field(
        default=None, description="Optional end timestamp for analysis window"
    )
    metric_filter: list[str] | None = Field(
        default=None, description="Optional list of specific metric names to analyze"
    )


class AnalyticsRunResponse(BaseModel):
    """Audit and execution result of an analytics run."""

    run_id: uuid.UUID
    company_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    records_analyzed: int = 0
    anomalies_detected: int = 0
    incident_candidates_generated: int = 0
    metrics_analyzed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BusinessImpactEstimateResponse(BaseModel):
    """Estimated blast radius for an incident candidate."""

    estimated_revenue_impact: float = 0.0
    estimated_orders_affected: int = 0
    estimated_users_affected: int = 0
    additional_support_tickets: int = 0
    additional_complaints: int = 0
    is_preliminary: bool = True


class IncidentCandidateResponse(BaseModel):
    """Correlated candidate incident generated from multi-metric anomaly clustering."""

    candidate_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    summary: str
    severity: str
    correlation_score: float
    first_detected_at: datetime
    last_detected_at: datetime
    affected_metrics: list[str] = Field(default_factory=list)
    anomaly_ids: list[uuid.UUID] = Field(default_factory=list)
    impact: BusinessImpactEstimateResponse
    created_at: datetime
