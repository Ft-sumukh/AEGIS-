"""Action lifecycle state machine with strictly validated transitions."""

from typing import TYPE_CHECKING

from app.models.enums import (
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionStatus,
)

if TYPE_CHECKING:
    from app.models.action import Action


class InvalidActionStateTransitionError(Exception):
    """Raised when an illegal action lifecycle transition is attempted."""

    def __init__(self, current_status: ActionStatus, target_status: ActionStatus, reason: str | None = None) -> None:
        msg = f"Cannot transition action from '{current_status}' to '{target_status}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason


# Centralized state transition graph
LEGAL_TRANSITIONS: dict[ActionStatus, set[ActionStatus]] = {
    ActionStatus.PROPOSED: {
        ActionStatus.PENDING_APPROVAL,
        ActionStatus.REJECTED,
    },
    ActionStatus.PENDING_APPROVAL: {
        ActionStatus.APPROVED,
        ActionStatus.REJECTED,
        ActionStatus.EXPIRED,
    },
    ActionStatus.APPROVED: {
        ActionStatus.EXECUTING,
        ActionStatus.REJECTED,
        ActionStatus.EXPIRED,
    },
    ActionStatus.EXECUTING: {
        ActionStatus.EXECUTED,
        ActionStatus.FAILED,
    },
    ActionStatus.EXECUTED: {
        ActionStatus.VERIFYING,
    },
    ActionStatus.VERIFYING: {
        ActionStatus.VERIFIED,
        ActionStatus.VERIFICATION_FAILED,
    },
    # Terminal states (cannot transition further without a new action proposal)
    ActionStatus.REJECTED: set(),
    ActionStatus.EXPIRED: set(),
    ActionStatus.FAILED: set(),
    ActionStatus.VERIFIED: set(),
    ActionStatus.VERIFICATION_FAILED: set(),
}


def can_transition(current_status: ActionStatus, target_status: ActionStatus) -> bool:
    """Checks whether a proposed status transition is permitted by the state machine."""
    allowed = LEGAL_TRANSITIONS.get(current_status, set())
    return target_status in allowed


def transition_action_status(
    action: "Action",
    target_status: ActionStatus,
    reason: str | None = None,
) -> None:
    """Validates and executes an action status transition on the given Action model instance.

    Also synchronizes legacy approval_status and execution_status columns for complete
    backward compatibility with existing database fixtures and queries.
    """
    current_status = action.status
    if not can_transition(current_status, target_status):
        raise InvalidActionStateTransitionError(
            current_status=current_status,
            target_status=target_status,
            reason=reason,
        )

    action.status = target_status

    # Synchronize legacy fields
    if target_status == ActionStatus.PENDING_APPROVAL:
        action.approval_status = ActionApprovalStatus.PENDING
    elif target_status == ActionStatus.APPROVED:
        action.approval_status = ActionApprovalStatus.APPROVED
    elif target_status == ActionStatus.REJECTED:
        action.approval_status = ActionApprovalStatus.REJECTED
    elif target_status == ActionStatus.EXECUTING:
        action.execution_status = ActionExecutionStatus.RUNNING
    elif target_status in (ActionStatus.EXECUTED, ActionStatus.VERIFYING, ActionStatus.VERIFIED):
        action.execution_status = ActionExecutionStatus.SUCCEEDED
    elif target_status in (ActionStatus.FAILED, ActionStatus.VERIFICATION_FAILED):
        action.execution_status = ActionExecutionStatus.FAILED

    # Broadcast real-time event to connected operations consoles
    try:
        from app.core.events import broadcast_event_sync

        broadcast_event_sync(
            event_type=f"ACTION_{target_status.value.upper()}",
            payload={
                "action_id": str(action.id),
                "action_type": action.action_type,
                "target_service": action.target_service,
                "previous_status": current_status.value,
                "new_status": target_status.value,
                "risk_level": action.risk_level.value if hasattr(action.risk_level, "value") else str(action.risk_level),
            },
            company_id=str(action.company_id) if action.company_id else None,
        )
    except Exception:
        pass
