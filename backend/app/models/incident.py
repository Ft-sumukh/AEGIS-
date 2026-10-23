"""Incident, IncidentEvidence, and IncidentNote entity models."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.anomaly import incident_anomalies
from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.action import Action
    from app.models.anomaly import Anomaly
    from app.models.company import Company
    from app.models.investigation import Investigation
    from app.models.recommendation import Recommendation


class Incident(Base):
    """Central operational incident entity aggregating correlated anomalies, evidence, and investigations."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_company_status", "company_id", "status"),
        Index("ix_incidents_company_severity_status", "company_id", "severity", "status"),
        Index("ix_incidents_company_detected_at", "company_id", "detected_at"),
        Index("ix_incidents_company_fingerprint", "company_id", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.HIGH,
        nullable=False,
        index=True,
    )
    severity_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(PortableJSON(), default=list, nullable=False)
    affected_systems: Mapped[list[str]] = mapped_column(
        PortableJSON(), default=list, nullable=False
    )
    affected_metrics: Mapped[list[str]] = mapped_column(
        PortableJSON(), default=list, nullable=False
    )

    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    investigation_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    mitigated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    # Human interaction & governance
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Recovery & deduplication
    recovery_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    confidence: Mapped[float | None] = mapped_column(nullable=True)
    estimated_revenue_impact: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_orders_affected: Mapped[int | None] = mapped_column(nullable=True)
    estimated_users_affected: Mapped[int | None] = mapped_column(nullable=True)
    estimated_support_impact: Mapped[int | None] = mapped_column(nullable=True)

    incident_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="incidents")
    anomalies: Mapped[list["Anomaly"]] = relationship(
        "Anomaly", secondary=incident_anomalies, back_populates="incidents"
    )
    evidence: Mapped[list["IncidentEvidence"]] = relationship(
        "IncidentEvidence", back_populates="incident", cascade="all, delete-orphan"
    )
    notes: Mapped[list["IncidentNote"]] = relationship(
        "IncidentNote", back_populates="incident", cascade="all, delete-orphan"
    )
    investigations: Mapped[list["Investigation"]] = relationship(
        "Investigation", back_populates="incident", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="incident", cascade="all, delete-orphan"
    )
    actions: Mapped[list["Action"]] = relationship(
        "Action", back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvidence(Base):
    """First-class evidence items linked to an incident for AI investigator reasoning."""

    __tablename__ = "incident_evidence"
    __table_args__ = (
        Index("ix_incident_evidence_incident_observed", "incident_id", "observed_at"),
        Index(
            "ix_incident_evidence_unique_source",
            "incident_id",
            "source_type",
            "source_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType, native_enum=False),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="synthetic", nullable=False)
    source_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ingestion_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    relevance_score: Mapped[float] = mapped_column(default=1.0, nullable=False)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship
    incident: Mapped["Incident"] = relationship("Incident", back_populates="evidence")


class IncidentNote(Base):
    """Operator or system annotations attached to an operational incident."""

    __tablename__ = "incident_notes"
    __table_args__ = (Index("ix_incident_notes_incident_created", "incident_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationship
    incident: Mapped["Incident"] = relationship("Incident", back_populates="notes")
