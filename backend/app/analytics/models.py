"""Data contracts, transfer objects, and representations for the analytics subsystem."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.models.enums import DetectorType, SeverityLevel


@dataclass
class MetricPoint:
    """Individual time-series metric data point."""

    timestamp: datetime
    value: float
    dimensions: dict[str, Any] = field(default_factory=dict)
    metric_id: uuid.UUID | None = None


@dataclass
class MetricSeries:
    """Ordered collection of time-series observations for a single metric."""

    company_id: uuid.UUID
    metric_name: str
    unit: str
    points: list[MetricPoint] = field(default_factory=list)

    def sort_by_timestamp(self) -> None:
        """Sorts points chronologically."""
        self.points.sort(key=lambda p: p.timestamp)

    @property
    def timestamps(self) -> list[datetime]:
        return [p.timestamp for p in self.points]

    @property
    def values(self) -> list[float]:
        return [p.value for p in self.points]


@dataclass
class BaselineResult:
    """Statistical baseline values calculated for a specific timestamp and metric."""

    expected_value: float
    standard_deviation: float
    sample_count: int
    baseline_type: str
    is_valid: bool = True
    error_reason: str | None = None


@dataclass
class RawAnomaly:
    """Intermediate anomaly candidate emitted by an individual detector."""

    metric_name: str
    timestamp: datetime
    observed_value: float
    expected_value: float
    deviation: float
    detector_type: DetectorType
    confidence: float
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    metric_id: uuid.UUID | None = None


@dataclass
class AnomalyScore:
    """Scoring evaluation establishing severity, confidence, and explainability."""

    severity: SeverityLevel
    confidence: float
    explanation: str
    fingerprint: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessImpactEstimate:
    """Estimated operational and business blast radius for an anomaly or incident candidate."""

    estimated_revenue_impact: Decimal = Decimal("0.00")
    estimated_orders_affected: int = 0
    estimated_users_affected: int = 0
    additional_support_tickets: int = 0
    additional_complaints: int = 0
    is_preliminary: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_revenue_impact": float(self.estimated_revenue_impact),
            "estimated_orders_affected": self.estimated_orders_affected,
            "estimated_users_affected": self.estimated_users_affected,
            "additional_support_tickets": self.additional_support_tickets,
            "additional_complaints": self.additional_complaints,
            "is_preliminary": self.is_preliminary,
        }


@dataclass
class IncidentCandidate:
    """Correlated cluster of concurrent, causally-linked operational anomalies."""

    candidate_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    preliminary_summary: str
    severity: SeverityLevel
    correlation_score: float
    first_detected_at: datetime
    last_detected_at: datetime
    affected_metrics: list[str]
    anomaly_ids: list[uuid.UUID] = field(default_factory=list)
    impact: BusinessImpactEstimate = field(default_factory=BusinessImpactEstimate)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": str(self.candidate_id),
            "company_id": str(self.company_id),
            "title": self.title,
            "summary": self.preliminary_summary,
            "severity": self.severity.value,
            "correlation_score": round(self.correlation_score, 3),
            "first_detected_at": self.first_detected_at.isoformat(),
            "last_detected_at": self.last_detected_at.isoformat(),
            "affected_metrics": self.affected_metrics,
            "anomaly_ids": [str(a) for a in self.anomaly_ids],
            "impact": self.impact.to_dict(),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AnalysisRunRecord:
    """Audit and status record for an executed analytics batch run."""

    run_id: uuid.UUID
    company_id: uuid.UUID
    status: str  # PENDING, RUNNING, COMPLETED, FAILED
    started_at: datetime
    completed_at: datetime | None = None
    records_analyzed: int = 0
    anomalies_detected: int = 0
    incident_candidates_generated: int = 0
    metrics_analyzed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "company_id": str(self.company_id),
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                round((self.completed_at - self.started_at).total_seconds(), 2)
                if self.completed_at
                else None
            ),
            "records_analyzed": self.records_analyzed,
            "anomalies_detected": self.anomalies_detected,
            "incident_candidates_generated": self.incident_candidates_generated,
            "metrics_analyzed": self.metrics_analyzed,
            "errors": self.errors,
        }
