"""Pydantic schemas for OperationalMetric telemetry entities."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationalMetricBase(BaseModel):
    company_id: uuid.UUID
    metric_name: str = Field(..., max_length=100)
    timestamp: datetime
    value: float
    unit: str = Field(..., max_length=50)
    source: str = Field(..., max_length=100)
    dimension_data: dict[str, Any] = Field(default_factory=dict)


class OperationalMetricCreate(OperationalMetricBase):
    pass


class OperationalMetricRead(OperationalMetricBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
