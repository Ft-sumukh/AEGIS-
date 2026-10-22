"""SupportTicket and CustomerComplaint entity models for operational feedback correlation."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SeverityLevel, TicketPriority, TicketStatus
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.customer import Customer


class SupportTicket(Base):
    """Customer support tickets representing customer-facing degradation symptoms."""

    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_company_status_created", "company_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ticket_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="support_tickets")
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="support_tickets")


class CustomerComplaint(Base):
    """Customer complaints indicating business and customer sentiment impact."""

    __tablename__ = "customer_complaints"
    __table_args__ = (Index("ix_customer_complaints_company_created", "company_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.MEDIUM,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    complaint_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="complaints")
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="complaints")
