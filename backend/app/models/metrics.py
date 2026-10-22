"""OperationalMetric entity model representing time-series telemetry data."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class OperationalMetric(Base):
    """Time-series operational metric measurement (e.g. error rate, latency, revenue, active users)."""

    __tablename__ = "operational_metrics"
    __table_args__ = (
        Index("ix_metrics_company_timestamp", "company_id", "timestamp"),
        Index("ix_metrics_company_name_timestamp", "company_id", "metric_name", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)

    # Multi-dimensional attributes (e.g. region, service, environment, channel)
    dimension_data: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Distributed Tracing & Lineage Metadata
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingestion_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship
    company: Mapped["Company"] = relationship("Company", back_populates="metrics")
