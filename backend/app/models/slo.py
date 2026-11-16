"""Service Level Objective (SLO) and Error Budget entity models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class ServiceLevelObjective(Base):
    """Represents a Service Level Objective (SLO) tracking SLI, Error Budget, and Multi-Window Burn Rates."""

    __tablename__ = "service_level_objectives"
    __table_args__ = (
        Index("ix_slo_company_service", "company_id", "service_name"),
        Index("ix_slo_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # SLO Targets
    target_percentage: Mapped[float] = mapped_column(Float, default=99.9, nullable=False)  # e.g. 99.9%
    sli_metric_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. api_error_rate
    sli_type: Mapped[str] = mapped_column(String(50), default="AVAILABILITY", nullable=False)  # AVAILABILITY, LATENCY
    time_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # 30-day rolling

    # Dynamic Error Budget & Real-Time Performance
    current_sli: Mapped[float] = mapped_column(Float, default=99.95, nullable=False)
    error_budget_remaining_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    burn_rate_1h: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 1.0 = normal consumption
    burn_rate_6h: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    burn_rate_24h: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    time_to_exhaustion_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status: HEALTHY, WARNING, BURNING, EXHAUSTED
    status: Mapped[str] = mapped_column(String(30), default="HEALTHY", nullable=False)

    metadata_info: Mapped[dict[str, Any]] = mapped_column(
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
    company: Mapped["Company"] = relationship("Company", back_populates="slos")
