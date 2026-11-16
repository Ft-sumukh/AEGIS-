"""Pydantic schemas for SystemEvent and Deployment entities."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeploymentStatus, SeverityLevel


class SystemEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    event_type: str
    severity: SeverityLevel
    service: str
    environment: str
    message: str
    timestamp: datetime
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DeploymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    service: str
    version: str
    environment: str
    status: DeploymentStatus
    deployed_at: datetime
    deployed_by: str
    deployment_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
