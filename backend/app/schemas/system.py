"""Pydantic schemas for operational system/service health."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.metrics import OperationalMetricRead


class SystemHealthRead(BaseModel):
    """Health and performance status of a registered service."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    status: str  # HEALTHY, DEGRADED, CRITICAL
    category: str = "service"
    error_rate: float = 0.0
    latency_ms: float = 0.0
    active_incidents: int = 0
    recent_anomalies: int = 0
    last_deployment: dict[str, Any] | None = None


class SystemDetailRead(SystemHealthRead):
    """Detailed telemetry and dependency view of a system."""

    dependencies: dict[str, list[str]] = Field(
        default_factory=lambda: {"upstream": [], "downstream": []}
    )
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    recent_deployments: list[dict[str, Any]] = Field(default_factory=list)
    metrics_history: list[OperationalMetricRead] = Field(default_factory=list)
    related_incidents: list[dict[str, Any]] = Field(default_factory=list)
