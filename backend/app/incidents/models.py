"""Data contracts, transfer objects, and models for Incident Management subsystem."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel


@dataclass
class TimelineEvent:
    """Normalized, unified chronological timeline event for an incident."""

    event_id: str
    event_type: str  # DEPLOYMENT, SYSTEM_EVENT, ANOMALY, METRIC_CHANGE, SUPPORT_TICKET, CUSTOMER_COMPLAINT, INCIDENT_CREATED, STATUS_CHANGED, EVIDENCE_ADDED, NOTE_ADDED
    timestamp: datetime
    title: str
    summary: str
    severity: SeverityLevel | None = None
    source_type: EvidenceSourceType | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "summary": self.summary,
            "severity": self.severity.value if self.severity else None,
            "source_type": self.source_type.value if self.source_type else None,
            "source_id": self.source_id,
            "metadata": self.metadata,
        }


@dataclass
class ImpactDelta:
    """Tracks change between successive business blast radius estimations."""

    current_revenue: float
    previous_revenue: float
    revenue_delta: float
    current_orders: int
    previous_orders: int
    orders_delta: int
    current_users: int
    previous_users: int
    users_delta: int
    current_support: int
    previous_support: int
    support_delta: int
    is_preliminary: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_revenue": self.current_revenue,
            "previous_revenue": self.previous_revenue,
            "revenue_delta": self.revenue_delta,
            "current_orders": self.current_orders,
            "previous_orders": self.previous_orders,
            "orders_delta": self.orders_delta,
            "current_users": self.current_users,
            "previous_users": self.previous_users,
            "users_delta": self.users_delta,
            "current_support": self.current_support,
            "previous_support": self.previous_support,
            "support_delta": self.support_delta,
            "is_preliminary": self.is_preliminary,
        }


@dataclass
class DeduplicationResult:
    """Result of an incident fingerprint deduplication evaluation."""

    is_duplicate: bool
    fingerprint: str
    existing_incident_id: uuid.UUID | None = None


class InvalidLifecycleTransitionError(ValueError):
    """Raised when an illegal incident state machine transition is attempted."""

    def __init__(self, from_status: IncidentStatus, to_status: IncidentStatus, reason: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        super().__init__(
            f"Cannot transition incident from '{from_status.value}' to '{to_status.value}': {reason}"
        )
