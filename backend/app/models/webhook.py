"""Webhook Subscription entity model for external event integrations."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class WebhookSubscription(Base):
    """External webhook subscription configuration for third-party alerts and notifications."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_type: Mapped[str] = mapped_column(String(50), default="GENERIC_WEBHOOK", nullable=False)
    subscribed_events: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)

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

    # Relationship
    company: Mapped["Company"] = relationship("Company", back_populates="webhooks")
