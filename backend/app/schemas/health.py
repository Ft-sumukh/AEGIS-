"""Schemas for health and readiness endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "unhealthy"] = Field(
        default="healthy", description="Application liveness status"
    )
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current runtime environment")


class ReadinessResponse(BaseModel):
    """Readiness probe response model verifying dependent subsystems."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "degraded", "not_ready"] = Field(
        ..., description="Overall service readiness"
    )
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Application version")
    database: Literal["connected", "unreachable"] = Field(
        ..., description="Database connectivity state"
    )
    latency_ms: float | None = Field(
        default=None, description="Database ping latency in milliseconds"
    )
    detail: str | None = Field(default=None, description="Diagnostic detail if degraded")
