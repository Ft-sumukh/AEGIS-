"""Telemetry source state model for persistent source tracking."""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.types import UTCDateTime
from app.telemetry.schemas import SourceStatus, TelemetrySourceType


class TelemetrySourceState(Base):
    """Persistent operational state and health statistics of registered telemetry sources."""

    __tablename__ = "telemetry_source_states"
    __table_args__ = (
        Index("ix_telemetry_source_name", "source", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    source_type: Mapped[TelemetrySourceType] = mapped_column(
        Enum(TelemetrySourceType, native_enum=False),
        default=TelemetrySourceType.SYNTHETIC,
        nullable=False,
    )
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False),
        default=SourceStatus.HEALTHY,
        nullable=False,
        index=True,
    )
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_success_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
