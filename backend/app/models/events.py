"""SystemEvent and Deployment entity models representing infrastructure state transitions."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import DeploymentStatus, SeverityLevel
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class SystemEvent(Base):
    """Normalized technical and operational infrastructure events."""

    __tablename__ = "system_events"
    __table_args__ = (
        Index("ix_system_events_company_timestamp", "company_id", "timestamp"),
        Index("ix_system_events_company_service_timestamp", "company_id", "service", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.INFO,
        nullable=False,
    )
    service: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Telemetry Source & Distributed Tracing
    source: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
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
    company: Mapped["Company"] = relationship("Company", back_populates="events")


class Deployment(Base):
    """Service deployment records. Used for AI root-cause correlation against anomaly timestamps."""

    __tablename__ = "deployments"
    __table_args__ = (
        Index("ix_deployments_company_service_deployed_at", "company_id", "service", "deployed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, native_enum=False),
        default=DeploymentStatus.STARTED,
        nullable=False,
    )
    deployed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    deployed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    deployment_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship
    company: Mapped["Company"] = relationship("Company", back_populates="deployments")
