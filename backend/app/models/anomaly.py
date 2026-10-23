"""Anomaly entity model and incident_anomalies association table."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Enum, ForeignKey, Index, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AnomalyStatus, DetectorType, SeverityLevel
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.incident import Incident
    from app.models.metrics import OperationalMetric

# Many-to-Many association table between Incidents and Anomalies
incident_anomalies = Table(
    "incident_anomalies",
    Base.metadata,
    Column("incident_id", Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("anomaly_id", Uuid, ForeignKey("anomalies.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_incident_anomalies_incident_id", "incident_id"),
    Index("ix_incident_anomalies_anomaly_id", "anomaly_id"),
)


class Anomaly(Base):
    """Represents an unusual observation detected by the analytics/anomaly engine."""

    __tablename__ = "anomalies"
    __table_args__ = (
        Index("ix_anomalies_company_detected_at", "company_id", "detected_at"),
        Index("ix_anomalies_company_status", "company_id", "status"),
        Index("ix_anomalies_company_severity", "company_id", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("operational_metrics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    observed_value: Mapped[float] = mapped_column(nullable=False)
    expected_value: Mapped[float] = mapped_column(nullable=False)
    deviation: Mapped[float] = mapped_column(nullable=False)
    detector_type: Mapped[DetectorType] = mapped_column(
        Enum(DetectorType, native_enum=False),
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.MEDIUM,
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus, native_enum=False),
        default=AnomalyStatus.NEW,
        nullable=False,
        index=True,
    )
    anomaly_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="anomalies")
    metric: Mapped["OperationalMetric | None"] = relationship("OperationalMetric")
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident", secondary=incident_anomalies, back_populates="anomalies"
    )
