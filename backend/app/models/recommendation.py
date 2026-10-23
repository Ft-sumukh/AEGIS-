"""Recommendation entity model representing proposed operational mitigations."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import RecommendationStatus, SeverityLevel, TicketPriority
from app.models.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.action import Action
    from app.models.incident import Incident
    from app.models.investigation import Investigation


class Recommendation(Base):
    """Corrective recommendation formulated by AI investigator, distinct from actual action execution."""

    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_incident_status", "incident_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False),
        default=TicketPriority.HIGH,
        nullable=False,
    )
    risk_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.MEDIUM,
        nullable=False,
    )
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, native_enum=False),
        default=RecommendationStatus.PROPOSED,
        nullable=False,
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
    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="recommendations"
    )
    incident: Mapped["Incident"] = relationship("Incident", back_populates="recommendations")
    actions: Mapped[list["Action"]] = relationship(
        "Action", back_populates="recommendation", cascade="all, delete-orphan"
    )
