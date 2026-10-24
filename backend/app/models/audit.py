"""AuditLog entity model providing immutable, append-only traceability."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AuditActorType
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.company import Company


class AuditLog(Base):
    """Immutable audit trail for compliance, security, and traceability.

    DESIGN PRINCIPLE:
    - Append-only. Audit records must NEVER be cascade deleted when parent
      business entities are removed (company_id ondelete="SET NULL").
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_company_timestamp", "company_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(AuditActorType, native_enum=False),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Relationship
    company: Mapped["Company | None"] = relationship("Company", back_populates="audit_logs")
