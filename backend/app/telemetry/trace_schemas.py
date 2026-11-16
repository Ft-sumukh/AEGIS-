"""Pydantic schemas and normalized contracts for distributed tracing."""

import uuid
from datetime import UTC, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.telemetry.schemas import TelemetrySourceType


class RawSpanPayload(BaseModel):
    """Raw span data submitted via batch ingestion."""
    model_config = ConfigDict(extra="allow")

    trace_id: Optional[str] = Field(default=None, alias="traceId")
    span_id: Optional[str] = Field(default=None, alias="spanId")
    parent_span_id: Optional[str] = Field(default=None, alias="parentSpanId")
    name: Optional[str] = None
    service_name: Optional[str] = Field(default=None, alias="service")
    environment: Optional[str] = None
    start_time: Optional[Any] = Field(default=None, alias="startTime")
    end_time: Optional[Any] = Field(default=None, alias="endTime")
    duration_ms: Optional[float] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    kind: Optional[str] = None


class BatchTracePayload(BaseModel):
    """Batch payload for trace ingestion API."""

    source: str = Field(default="opentelemetry", description="Identifier of the emitting telemetry source")
    source_type: TelemetrySourceType = Field(default=TelemetrySourceType.OTEL)
    spans: list[dict[str, Any]] = Field(..., description="Array of raw span items or OTLP span dicts")


class NormalizedSpanRecord(BaseModel):
    """Normalized distributed trace span with standardized timing and sanitized attributes."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    company_id: Optional[uuid.UUID] = None

    trace_id: str = Field(..., description="W3C Trace ID (hex 16 or 32 chars)")
    span_id: str = Field(..., description="W3C Span ID (hex 16 chars)")
    parent_span_id: Optional[str] = Field(default=None, description="Parent Span ID if not root")

    timestamp_start: datetime = Field(..., description="UTC start time")
    timestamp_end: datetime = Field(..., description="UTC end time")
    duration_ms: float = Field(..., ge=0.0, description="Span duration in milliseconds")

    service_name: str = Field(..., description="Canonical service identity")
    service_version: Optional[str] = None
    environment: str = Field(default="production")
    operation_name: str = Field(default="operation", description="Span or endpoint name")
    span_kind: str = Field(default="SERVER")

    status: str = Field(default="OK", description="OK, ERROR, or UNSET")
    status_message: Optional[str] = None

    # Protocols & Metadata
    http_method: Optional[str] = None
    http_route: Optional[str] = None
    http_status_code: Optional[int] = None
    rpc_system: Optional[str] = None
    rpc_service: Optional[str] = None
    rpc_method: Optional[str] = None
    database_system: Optional[str] = None
    database_operation: Optional[str] = None
    peer_service: Optional[str] = None
    host: Optional[str] = None
    trace_flags: Optional[str] = None

    source: str = Field(default="opentelemetry")
    schema_version: str = Field(default="1.0")
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    sanitized_attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp_start", "timestamp_end", mode="before")
    @classmethod
    def ensure_utc(cls, v: Any) -> datetime:
        if isinstance(v, (int, float)):
            if v > 1e15:  # nanoseconds
                v = v / 1_000_000_000.0
            elif v > 1e11:  # milliseconds
                v = v / 1000.0
            return datetime.fromtimestamp(v, tz=UTC)
        if isinstance(v, str):
            cleaned = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        return datetime.now(UTC)


class TraceSpanNode(BaseModel):
    """Hierarchical node in a reconstructed trace tree."""

    id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    service_version: Optional[str] = None
    environment: str
    operation_name: str
    span_kind: str
    status: str
    status_message: Optional[str] = None
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: float
    self_time_ms: float
    start_offset_ms: float = 0.0

    http_method: Optional[str] = None
    http_route: Optional[str] = None
    http_status_code: Optional[int] = None
    peer_service: Optional[str] = None
    host: Optional[str] = None

    sanitized_attributes: dict[str, Any] = Field(default_factory=dict)
    children: list["TraceSpanNode"] = Field(default_factory=list)


class CriticalPathSegment(BaseModel):
    """Segment along the latency-determining critical execution path."""

    span_id: str
    service_name: str
    operation_name: str
    duration_ms: float
    self_time_ms: float
    contribution_percent: float
    description: str


class CriticalPathResponse(BaseModel):
    """Deterministic critical path calculation result."""

    trace_id: str
    total_duration_ms: float
    critical_path_duration_ms: float
    segments: list[CriticalPathSegment]
    non_causal_assessment: str


class ErrorPropagationStep(BaseModel):
    """A step in an observed error propagation chain."""

    span_id: str
    service_name: str
    operation_name: str
    status: str
    http_status_code: Optional[int] = None
    timestamp: datetime
    error_message: Optional[str] = None
    is_deepest_error: bool = False


class ErrorPropagationResponse(BaseModel):
    """Structured error propagation evidence across service boundaries."""

    trace_id: str
    has_errors: bool
    root_error_service: Optional[str] = None
    root_error_span_id: Optional[str] = None
    root_error_status_code: Optional[int] = None
    root_error_message: Optional[str] = None
    propagation_chain: list[ErrorPropagationStep] = Field(default_factory=list)
    non_causal_assessment: str


class TraceTreeResponse(BaseModel):
    """Complete trace hierarchy with summary and analysis."""

    trace_id: str
    root_span: Optional[TraceSpanNode] = None
    spans_count: int
    total_duration_ms: float
    services: list[str]
    status: str
    error_count: int
    critical_path: Optional[CriticalPathResponse] = None
    error_propagation: Optional[ErrorPropagationResponse] = None


class TraceSummaryItem(BaseModel):
    """Summary item for trace exploration and list endpoints."""

    trace_id: str
    timestamp_start: datetime
    duration_ms: float
    root_service: str
    root_operation: str
    status: str
    span_count: int
    error_count: int
    services: list[str]
    environment: str


class ServiceDependencyItem(BaseModel):
    """Directed caller -> callee service dependency metrics."""

    source_service: str
    target_service: str
    environment: str
    request_count: int
    error_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    first_seen: datetime
    last_seen: datetime


class ServiceDependencyGraphResponse(BaseModel):
    """Service dependency topology graph."""

    nodes: list[dict[str, Any]]
    edges: list[ServiceDependencyItem]
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None


class ServiceTraceHealthResponse(BaseModel):
    """Service health snapshot derived from traces."""

    service_name: str
    environment: str
    request_count: int
    error_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    slow_request_count: int
    slow_request_percent: float
    dependency_failures: int
    trace_anomaly_count: int
    health_status: str  # HEALTHY, DEGRADED, FAILED


class TraceIngestionResult(BaseModel):
    """Result of trace span batch ingestion."""

    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    malformed: int = 0
    source: str
    batch_id: str
    errors: list[str] = Field(default_factory=list)
