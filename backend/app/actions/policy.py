"""Action policy engine enforcing RBAC, approval validity, separation of duties, and AI restrictions."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import (
    ActionStatus,
    ActionType,
    AuditActorType,
    SeverityLevel,
)
from app.security.auth import ROLE_HIERARCHY, AuthUser, UserRole

if TYPE_CHECKING:
    from app.models.action import Action


class ActionPolicyViolationError(Exception):
    """Raised when an action operation violates platform governance policies."""
    pass


class AIApprovalForbiddenError(ActionPolicyViolationError):
    """Raised when an autonomous AI agent identity attempts to approve or execute an action."""
    pass


class ActionApprovalExpiredError(ActionPolicyViolationError):
    """Raised when an approved action has exceeded its validity TTL window."""
    pass


class ConcurrentActionConflictError(ActionPolicyViolationError):
    """Raised when another action is already actively executing against the same target service."""
    pass


class SeparationOfDutiesError(ActionPolicyViolationError):
    """Raised when the same operator attempts to request and approve high-risk actions under strict policy."""
    pass


class ActionPolicyEngine:
    """Centralized policy engine governing action proposal, human authorization, and execution gating."""

    @classmethod
    def is_ai_identity(cls, user: AuthUser) -> bool:
        """Determines if the actor identity represents an autonomous AI agent rather than a verified human."""
        name_lower = user.username.lower()
        id_lower = user.user_id.lower()
        ai_markers = ("agent", "aegis", "investigator", "llm", "bot")
        return any(m in name_lower or m in id_lower for m in ai_markers)

    @classmethod
    def validate_can_propose(cls, user: AuthUser, action_type: ActionType) -> None:
        """Validates if the user is authorized to create an action proposal.

        Analysts, Operators, Admins, and AI Agents may formulate proposals. Viewers cannot.
        """
        if user.role == UserRole.VIEWER:
            raise ActionPolicyViolationError(
                f"Role '{user.role}' is read-only. Cannot propose operational actions."
            )

    @classmethod
    def validate_can_approve(
        cls,
        user: AuthUser,
        action: "Action",
    ) -> None:
        """Enforces human authorization gating.

        Hard Requirement: The AI is strictly prohibited from approving its own or any other action.
        """
        # 1. Hard AI Gating: Autonomous agents can NEVER approve actions
        if cls.is_ai_identity(user):
            raise AIApprovalForbiddenError(
                "Autonomous AI agents are strictly forbidden from approving operational actions. "
                "Approval must originate from an authenticated human operator or administrator."
            )

        # 2. Role Gating based on Action Risk
        user_weight = ROLE_HIERARCHY.get(user.role, 0)

        if action.risk_level == SeverityLevel.CRITICAL:
            # Critical actions (e.g. PAUSE_TRAFFIC) require ADMIN authority
            if user.role != UserRole.ADMIN:
                raise ActionPolicyViolationError(
                    f"CRITICAL risk actions require ADMIN approval. Current role: '{user.role}'."
                )
        elif action.risk_level in (SeverityLevel.HIGH, SeverityLevel.MEDIUM):
            # High/Medium actions require OPERATOR or higher
            if user_weight < ROLE_HIERARCHY[UserRole.OPERATOR]:
                raise ActionPolicyViolationError(
                    f"Approval requires OPERATOR or ADMIN role. Role '{user.role}' is insufficient."
                )
        else:
            # Low risk requires at least OPERATOR
            if user_weight < ROLE_HIERARCHY[UserRole.OPERATOR]:
                raise ActionPolicyViolationError(
                    f"Approval requires at least OPERATOR role. Role '{user.role}' is insufficient."
                )

        # 3. Separation of Duties check (if configured)
        settings = get_settings()
        if settings.ENFORCE_SEPARATION_OF_DUTIES and action.risk_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
            if action.requested_by.strip().lower() == user.username.strip().lower():
                raise SeparationOfDutiesError(
                    f"Separation of duties policy active: Requester '{action.requested_by}' "
                    f"cannot approve their own {action.risk_level} action proposal."
                )

    @classmethod
    def validate_can_execute(
        cls,
        user: AuthUser,
        action: "Action",
    ) -> None:
        """Validates execution privileges and approval state immediately before execution starts."""
        # 1. AI cannot execute actions directly
        if cls.is_ai_identity(user):
            raise AIApprovalForbiddenError(
                "Autonomous AI agents are strictly forbidden from executing operational actions. "
                "Execution must be triggered by an authorized human operator or administrator."
            )

        # 2. Role Gating: Operators and Admins can execute approved actions
        user_weight = ROLE_HIERARCHY.get(user.role, 0)
        if action.risk_level == SeverityLevel.CRITICAL:
            if user.role != UserRole.ADMIN:
                raise ActionPolicyViolationError(
                    f"Executing CRITICAL actions requires ADMIN role. Current role: '{user.role}'."
                )
        elif user_weight < ROLE_HIERARCHY[UserRole.OPERATOR]:
            raise ActionPolicyViolationError(
                f"Executing actions requires OPERATOR or ADMIN role. Current role: '{user.role}'."
            )

        # 3. Action must be in APPROVED status
        if action.status != ActionStatus.APPROVED:
            raise ActionPolicyViolationError(
                f"Action cannot be executed in status '{action.status}'. Must be APPROVED."
            )

        # 4. Check approval expiration (TTL)
        now = datetime.now(UTC)
        if action.expires_at and now > action.expires_at:
            raise ActionApprovalExpiredError(
                f"Action approval expired at {action.expires_at.isoformat()} (Current: {now.isoformat()}). "
                "A fresh proposal and authorization is required."
            )

    @classmethod
    def calculate_expiration(cls, approved_at: datetime | None = None) -> datetime:
        """Calculates the approval expiration timestamp based on configured TTL."""
        settings = get_settings()
        base_time = approved_at or datetime.now(UTC)
        return base_time + timedelta(minutes=settings.ACTION_APPROVAL_TTL_MINUTES)

    @classmethod
    def check_target_concurrency(
        cls,
        db: Session,
        target_service: str | None,
        exclude_action_id: uuid.UUID | None = None,
    ) -> None:
        """Detects if another action is currently actively EXECUTING against the same target service."""
        if not target_service:
            return

        from app.models.action import Action

        stmt = select(Action).where(
            Action.target_service == target_service,
            Action.status == ActionStatus.EXECUTING,
        )
        if exclude_action_id:
            stmt = stmt.where(Action.id != exclude_action_id)

        conflicting = db.scalars(stmt).first()
        if conflicting:
            raise ConcurrentActionConflictError(
                f"Conflicting action '{conflicting.id}' is currently executing against target service '{target_service}'. "
                "Simultaneous mutations against the same target are blocked."
            )
