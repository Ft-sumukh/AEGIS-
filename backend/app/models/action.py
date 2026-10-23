"""Action entity model representing executable operational tasks with human-in-the-loop gating."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    ActionApprovalDecision,
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionStatus,
    ActionType,
    SeverityLevel,
    VerificationOutcome,
)
from app.models.types import PortableJSON, UTCDateTime

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.recommendation import Recommendation


class Action(Base):
    """Execution entity governed by human approval gating before infrastructure changes occur."""

    __tablename__ = "actions"
    __table_args__ = (
        Index("ix_actions_incident_execution", "incident_id", "execution_status"),
    )


    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core identification & lifecycle
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Operational Action",
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, native_enum=False),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        default=SeverityLevel.MEDIUM,
        nullable=False,
    )
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, native_enum=False),
        default=ActionStatus.PROPOSED,
        nullable=False,
        index=True,
    )

    # Legacy status fields maintained for full backward compatibility
    approval_status: Mapped[ActionApprovalStatus] = mapped_column(
        Enum(ActionApprovalStatus, native_enum=False),
        default=ActionApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    execution_status: Mapped[ActionExecutionStatus] = mapped_column(
        Enum(ActionExecutionStatus, native_enum=False),
        default=ActionExecutionStatus.NOT_STARTED,
        nullable=False,
        index=True,
    )

    # Action parameters & target specification
    target_service: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )
    preconditions: Mapped[list[str]] = mapped_column(
        PortableJSON(), default=list, nullable=False
    )
    expected_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Security immutability & concurrency
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Timestamps & actors
    requested_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Execution outcome
    execution_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )

    # Verification lifecycle
    verification_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_status: Mapped[VerificationOutcome | None] = mapped_column(
        Enum(VerificationOutcome, native_enum=False),
        nullable=True,
    )
    verification_result: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )
    verification_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

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
    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation", back_populates="actions"
    )
    incident: Mapped["Incident"] = relationship("Incident", back_populates="actions")
    approvals: Mapped[list["ActionApproval"]] = relationship(
        "ActionApproval",
        back_populates="action",
        cascade="all, delete-orphan",
        order_by="ActionApproval.created_at.desc()",
    )


class ActionApproval(Base):
    """Immutable audit record of human authorization decision for an action proposal."""

    __tablename__ = "action_approvals"
    __table_args__ = (Index("ix_action_approvals_action_decision", "action_id", "decision"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[ActionApprovalDecision] = mapped_column(
        Enum(ActionApprovalDecision, native_enum=False), nullable=False
    )
    decision_by: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint_verified: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_metadata: Mapped[dict[str, Any]] = mapped_column(
        PortableJSON(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationship
    action: Mapped["Action"] = relationship("Action", back_populates="approvals")
