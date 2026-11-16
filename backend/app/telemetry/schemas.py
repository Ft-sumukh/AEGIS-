"""
Pydantic schemas and normalized contracts for operational telemetry.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetrySourceType(StrEnum):
    SYNTHETIC = "SYNTHETIC"
    OTEL = "OTEL"
    PROMETHEUS = "PROMETHEUS"
    CLOUDWATCH = "CLOUDWATCH"
    DATADOG = "DATADOG"
    APPLICATION_LOG = "APPLICATION_LOG"
    DEPLOYMENT_SYSTEM = "DEPLOYMENT_SYSTEM"


class TelemetryEventType(StrEnum):
    METRIC = "METRIC"
    LOG = "LOG"
    TRACE = "TRACE"
    EVENT = "EVENT"
    DEPLOYMENT = "DEPLOYMENT"


class SourceStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class TelemetryRecord(BaseModel):
    """Normalized unified telemetry record for all data sources."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique event identifier")
    source: str = Field(..., description="Name or identifier of source system (e.g. prometheus-prod, otel-collector)")
    source_type: TelemetrySourceType = Field(default=TelemetrySourceType.SYNTHETIC)
    event_type: TelemetryEventType = Field(default=TelemetryEventType.METRIC)

    timestamp: datetime = Field(..., description="Timestamp when event occurred at source (UTC)")
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when Aegis ingested the record (UTC)",
    )

    service: str = Field(..., description="Normalized canonical service name (e.g. checkout-service)")
    environment: str = Field(default="production", description="Runtime environment: production, staging, development, demo")
    host: Optional[str] = Field(default=None, description="Host or container node identifier")

    # Metric-specific fields
    metric_name: Optional[str] = Field(default=None, description="Normalized metric name (e.g. api_latency)")
    value: Optional[float] = Field(default=None, description="Metric numeric value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. ms, seconds, ratio, count)")
    dimensions: dict[str, Any] = Field(default_factory=dict, description="Multi-dimensional labels and attributes")

    # Log/Event specific fields
    severity: str = Field(default="INFO", description="Severity: INFO, WARN, ERROR, CRITICAL")
    message: Optional[str] = Field(default=None, description="Human-readable log or event description")

    # Distributed Tracing context
    trace_id: Optional[str] = Field(default=None, description="W3C / OpenTelemetry Trace ID")
    span_id: Optional[str] = Field(default=None, description="OpenTelemetry Span ID")
    parent_span_id: Optional[str] = Field(default=None, description="Parent Span ID")

    # Metadata & Data Lineage
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary sanitized source metadata")
    schema_version: str = Field(default="1.0", description="Contract schema version")

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, (int, float)):
            # Convert epoch timestamp (seconds or milliseconds)
            if v > 1e11:
                v = v / 1000.0
            return datetime.fromtimestamp(v, tz=UTC)
        if isinstance(v, str):
            cleaned = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        raise ValueError(f"Invalid timestamp format: {v}")


class BatchTelemetryPayload(BaseModel):
    """Payload for batch push ingestion."""

    source: str = Field(..., description="Identifier of the emitting telemetry source")
    source_type: TelemetrySourceType = Field(default=TelemetrySourceType.OTEL)
    events: list[dict[str, Any]] = Field(..., description="Array of telemetry event items")


class IngestionResult(BaseModel):
    """Structured response from ingestion API."""

    accepted: int = Field(default=0, description="Count of accepted records")
    rejected: int = Field(default=0, description="Count of rejected/malformed records")
    duplicates: int = Field(default=0, description="Count of deduplicated records")
    source: str
    batch_id: str
    errors: list[str] = Field(default_factory=list, description="Validation or rejection reasons")


class SourceHealthStatus(BaseModel):
    """Live health and telemetry throughput status of a data source."""

    source: str
    source_type: TelemetrySourceType
    status: SourceStatus
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    records_received: int = 0
    records_rejected: int = 0
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    events_per_minute: float = 0.0


class DataQualityMetrics(BaseModel):
    """Aggregate telemetry data quality indicators."""

    records_received: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    duplicates_filtered: int = 0
    missing_fields_count: int = 0
    late_events_count: int = 0
    clock_skew_avg_seconds: float = 0.0
    active_sources_count: int = 0


class TelemetryExploreQuery(BaseModel):
    """Query parameters for telemetry exploration."""

    metric_name: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    source: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)


class TelemetryExploreItem(BaseModel):
    """Single explored telemetry item."""

    id: str
    timestamp: datetime
    ingestion_timestamp: datetime
    source: str
    service: str
    environment: str
    metric_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    severity: str
    message: Optional[str] = None
    trace_id: Optional[str] = None
