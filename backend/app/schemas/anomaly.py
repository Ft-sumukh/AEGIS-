"""Pydantic schemas for Anomaly entities."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnomalyStatus, DetectorType, SeverityLevel


class AnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    metric_id: uuid.UUID | None
    metric_name: str
    detected_at: datetime
    observed_value: float
    expected_value: float
    deviation: float
    detector_type: DetectorType
    severity: SeverityLevel
    confidence: float
    explanation: str
    status: AnomalyStatus
    anomaly_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AnomalySummary(BaseModel):
    """Statistical summary of detected anomalies."""

    total_anomalies: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_detector_type: dict[str, int] = Field(default_factory=dict)
    top_metrics: dict[str, int] = Field(default_factory=dict)
