"""TraceSpan entity model representing distributed tracing spans."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class TraceSpan(Base):
    """Normalized distributed trace span with OpenTelemetry semantics and optimized query indexes."""

    __tablename__ = "trace_spans"
    __table_args__ = (
        Index("ix_trace_spans_company_trace", "company_id", "trace_id"),
        Index("ix_trace_spans_company_service", "company_id", "service_name", "timestamp_start"),
        Index("ix_trace_spans_company_status", "company_id", "status", "timestamp_start"),
        Index("ix_trace_spans_duration", "company_id", "duration_ms"),
        Index("ix_trace_spans_trace_span", "trace_id", "span_id"),
        Index("ix_trace_spans_parent", "trace_id", "parent_span_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # W3C Distributed Tracing Identifiers
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Timing & Duration
    timestamp_start: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    timestamp_end: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Service & Operation Identity
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    environment: Mapped[str] = mapped_column(String(50), default="production", nullable=False, index=True)
    operation_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    # OpenTelemetry Span Kind (SERVER, CLIENT, PRODUCER, CONSUMER, INTERNAL)
    span_kind: Mapped[str] = mapped_column(String(30), default="SERVER", nullable=False)

    # Status & Error Semantics (OK, ERROR, UNSET)
    status: Mapped[str] = mapped_column(String(30), default="OK", nullable=False, index=True)
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Protocol & Metadata (HTTP, RPC, Database)
    http_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    http_route: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpc_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rpc_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rpc_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    database_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    database_operation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    peer_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    host: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    trace_flags: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Source & Lineage
    source: Mapped[str] = mapped_column(String(100), default="opentelemetry", nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Group 7 Sanitized Attributes (PII, credentials, and raw bodies redacted/stripped)
    sanitized_attributes: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="trace_spans")
