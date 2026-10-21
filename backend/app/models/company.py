"""Company entity model representing organizations using Aegis."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import CompanyStatus
from app.models.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.anomaly import Anomaly
    from app.models.audit import AuditLog
    from app.models.customer import Customer
    from app.models.events import Deployment, SystemEvent
    from app.models.incident import Incident
    from app.models.metrics import OperationalMetric
    from app.models.order import Order
    from app.models.slo import ServiceLevelObjective
    from app.models.support import CustomerComplaint, SupportTicket
    from app.models.trace import TraceSpan
    from app.models.webhook import WebhookSubscription


class Company(Base):
    """Represents an organization/enterprise tenant in Aegis."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, native_enum=False),
        default=CompanyStatus.ACTIVE,
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
    customers: Mapped[list["Customer"]] = relationship(
        "Customer", back_populates="company", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="company", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["OperationalMetric"]] = relationship(
        "OperationalMetric", back_populates="company", cascade="all, delete-orphan"
    )
    events: Mapped[list["SystemEvent"]] = relationship(
        "SystemEvent", back_populates="company", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="company", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="company", cascade="all, delete-orphan"
    )
    complaints: Mapped[list["CustomerComplaint"]] = relationship(
        "CustomerComplaint", back_populates="company", cascade="all, delete-orphan"
    )
    anomalies: Mapped[list["Anomaly"]] = relationship(
        "Anomaly", back_populates="company", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident", back_populates="company", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="company")
    trace_spans: Mapped[list["TraceSpan"]] = relationship(
        "TraceSpan", back_populates="company", cascade="all, delete-orphan"
    )
    slos: Mapped[list["ServiceLevelObjective"]] = relationship(
        "ServiceLevelObjective", back_populates="company", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["WebhookSubscription"]] = relationship(
        "WebhookSubscription", back_populates="company", cascade="all, delete-orphan"
    )
