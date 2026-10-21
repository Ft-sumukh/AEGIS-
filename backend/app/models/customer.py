"""Customer entity model for synthetic enterprise operations."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.order import Order
    from app.models.support import CustomerComplaint, SupportTicket


class Customer(Base):
    """Customer entity representing end-users in operational telemetry.

    PRIVACY NOTICE:
    - 'email' and 'phone' fields represent PII and are strictly designated for
      synthetic/demonstration data. In production environments, these fields must be
      tokenized, pseudonymized, or omitted by the Privacy Shield.
    """

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("company_id", "external_reference", name="uq_customers_company_ext_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # @sensitive: PII field
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # @sensitive: PII field
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    region: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

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
    company: Mapped["Company"] = relationship("Company", back_populates="customers")
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="customer", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="customer"
    )
    complaints: Mapped[list["CustomerComplaint"]] = relationship(
        "CustomerComplaint", back_populates="customer"
    )
