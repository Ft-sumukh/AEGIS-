"""Pydantic schemas for Action entities and Human Approval workflows."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActionApprovalDecision,
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionStatus,
    ActionType,
    SeverityLevel,
    VerificationOutcome,
)


class ActionApprovalRead(BaseModel):
    """Schema for individual human authorization audit records."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_id: uuid.UUID
    decision: ActionApprovalDecision
    decision_by: str
    decision_at: datetime
    reason: str | None = None
    fingerprint_verified: str
    approval_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ActionRead(BaseModel):
    """Detailed read schema for Action entities."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommendation_id: uuid.UUID
    incident_id: uuid.UUID
    title: str = "Operational Action"
    action_type: ActionType
    description: str
    risk_level: SeverityLevel
    status: ActionStatus = ActionStatus.PROPOSED
    approval_status: ActionApprovalStatus = ActionApprovalStatus.PENDING
    execution_status: ActionExecutionStatus = ActionExecutionStatus.NOT_STARTED

    target_service: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    expected_outcome: str | None = None

    fingerprint: str | None = None
    idempotency_key: str | None = None

    requested_at: datetime
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    started_at: datetime | None = None
    executed_at: datetime | None = None
    completed_at: datetime | None = None

    requested_by: str
    approved_by: str | None = None

    execution_result: str | None = None
    failure_reason: str | None = None
    action_metadata: dict[str, Any] = Field(default_factory=dict)

    verification_strategy: str | None = None
    verification_status: VerificationOutcome | None = None
    verification_result: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    approvals: list[ActionApprovalRead] = Field(default_factory=list)


ActionDetailRead = ActionRead


class ActionCreate(BaseModel):

    """Request payload for proposing an operational action."""

    recommendation_id: uuid.UUID
    title: str | None = None
    action_type: ActionType
    description: str | None = None
    risk_level: SeverityLevel | None = None
    target_service: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class ActionSubmitRequest(BaseModel):
    """Request payload for submitting an action proposal for human authorization."""

    notes: str | None = None


class ActionApprovalRequest(BaseModel):
    """Request payload for human authorization decision."""

    decision: ActionApprovalDecision = ActionApprovalDecision.APPROVED
    reason: str | None = None
    confirmation_phrase: str | None = Field(
        default=None,
        description="Explicit typed confirmation for HIGH/CRITICAL actions (e.g. 'APPROVE ROLLBACK')",
    )


class ActionRejectionRequest(BaseModel):
    """Request payload for rejecting an action proposal."""

    reason: str = Field(
        ...,
        min_length=3,
        description="Mandatory justification explaining why the action proposal was rejected",
    )


class ActionExecutionRequest(BaseModel):
    """Request payload for executing an approved action."""

    dry_run: bool = Field(
        default=False,
        description="When True, validates preconditions and policies without changing simulated state",
    )
    idempotency_key: str | None = None


class ActionListResponse(BaseModel):
    """Paginated list of actions."""

    items: list[ActionRead]
    total: int
    limit: int
    offset: int
