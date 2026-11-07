"""Pydantic schemas for high-level operations dashboard overview."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.incident import IncidentRead
from app.schemas.investigation import InvestigationRead
from app.schemas.metrics import OperationalMetricRead


class OverviewKpis(BaseModel):
    """Aggregated operational indicators."""

    active_incidents: int = 0
    critical_incidents: int = 0
    active_anomalies: int = 0
    affected_systems_count: int = 0
    estimated_revenue_impact: float = 0.0
    failed_orders_count: int = 0
    api_error_rate_current: float = 0.0
    checkout_failure_rate_current: float = 0.0


class OverviewResponse(BaseModel):
    """Consolidated payload for initial dashboard view."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "OPERATIONAL"
    environment: str = "production"
    company_name: str = "Acme Cloud Commerce"
    last_updated: str
    kpis: OverviewKpis
    recent_incidents: list[IncidentRead] = Field(default_factory=list)
    latest_investigation: InvestigationRead | None = None
    key_metrics: list[OperationalMetricRead] = Field(default_factory=list)
    systems_summary: list[dict[str, Any]] = Field(default_factory=list)
