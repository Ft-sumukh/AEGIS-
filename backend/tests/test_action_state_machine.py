"""Unit tests for Action State Machine."""

import uuid
import pytest

from app.actions.state_machine import (
    LEGAL_TRANSITIONS,
    InvalidActionStateTransitionError,
    can_transition,
    transition_action_status,
)
from app.models.action import Action
from app.models.enums import (
    ActionApprovalStatus,
    ActionExecutionStatus,
    ActionStatus,
    ActionType,
    SeverityLevel,
)


def test_legal_transitions_graph_completeness():
    """Verify core states have explicit outgoing transitions defined."""
    assert ActionStatus.PROPOSED in LEGAL_TRANSITIONS
    assert ActionStatus.PENDING_APPROVAL in LEGAL_TRANSITIONS[ActionStatus.PROPOSED]
    assert ActionStatus.APPROVED in LEGAL_TRANSITIONS[ActionStatus.PENDING_APPROVAL]
    assert ActionStatus.REJECTED in LEGAL_TRANSITIONS[ActionStatus.PENDING_APPROVAL]
    assert ActionStatus.EXECUTING in LEGAL_TRANSITIONS[ActionStatus.APPROVED]
    assert ActionStatus.EXECUTED in LEGAL_TRANSITIONS[ActionStatus.EXECUTING]
    assert ActionStatus.VERIFYING in LEGAL_TRANSITIONS[ActionStatus.EXECUTED]
    assert ActionStatus.VERIFIED in LEGAL_TRANSITIONS[ActionStatus.VERIFYING]


def test_can_transition_validation():
    """Verify can_transition returns true for valid steps and false for invalid ones."""
    assert can_transition(ActionStatus.PROPOSED, ActionStatus.PENDING_APPROVAL) is True
    assert can_transition(ActionStatus.PROPOSED, ActionStatus.EXECUTING) is False
    assert can_transition(ActionStatus.APPROVED, ActionStatus.EXECUTING) is True
    assert can_transition(ActionStatus.REJECTED, ActionStatus.APPROVED) is False
    assert can_transition(ActionStatus.VERIFIED, ActionStatus.EXECUTING) is False


def test_successful_action_lifecycle_transitions():
    """Verify state transition helper updates action and maintains backward compatibility."""
    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Test Action",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting service",
        risk_level=SeverityLevel.LOW,
        status=ActionStatus.PROPOSED,
        approval_status=ActionApprovalStatus.PENDING,
        execution_status=ActionExecutionStatus.NOT_STARTED,
        requested_by="operator_1",
    )

    # 1. Propose -> Submit for Approval
    transition_action_status(action, ActionStatus.PENDING_APPROVAL)
    assert action.status == ActionStatus.PENDING_APPROVAL
    assert action.approval_status == ActionApprovalStatus.PENDING

    # 2. Submit -> Approved
    transition_action_status(action, ActionStatus.APPROVED)
    assert action.status == ActionStatus.APPROVED
    assert action.approval_status == ActionApprovalStatus.APPROVED

    # 3. Approved -> Executing
    transition_action_status(action, ActionStatus.EXECUTING)
    assert action.status == ActionStatus.EXECUTING
    assert action.execution_status == ActionExecutionStatus.RUNNING

    # 4. Executing -> Executed
    transition_action_status(action, ActionStatus.EXECUTED)
    assert action.status == ActionStatus.EXECUTED
    assert action.execution_status == ActionExecutionStatus.SUCCEEDED

    # 5. Executed -> Verifying
    transition_action_status(action, ActionStatus.VERIFYING)
    assert action.status == ActionStatus.VERIFYING

    # 6. Verifying -> Verified
    transition_action_status(action, ActionStatus.VERIFIED)
    assert action.status == ActionStatus.VERIFIED


def test_rejected_action_transition():
    """Verify rejection path correctly updates approval_status."""
    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Test Action",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        description="Rollback",
        status=ActionStatus.PENDING_APPROVAL,
        approval_status=ActionApprovalStatus.PENDING,
        requested_by="operator_1",
    )

    transition_action_status(action, ActionStatus.REJECTED)
    assert action.status == ActionStatus.REJECTED
    assert action.approval_status == ActionApprovalStatus.REJECTED


def test_failed_action_transition():
    """Verify execution failure transition updates execution_status to FAILED."""
    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Test Action",
        action_type=ActionType.SCALE_SERVICE,
        description="Scaling",
        status=ActionStatus.EXECUTING,
        approval_status=ActionApprovalStatus.APPROVED,
        execution_status=ActionExecutionStatus.RUNNING,
        requested_by="operator_1",
    )

    transition_action_status(action, ActionStatus.FAILED)
    assert action.status == ActionStatus.FAILED
    assert action.execution_status == ActionExecutionStatus.FAILED


def test_illegal_transition_raises_error():
    """Verify illegal transitions raise InvalidActionStateTransitionError."""
    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Test Action",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting service",
        status=ActionStatus.PROPOSED,
        requested_by="operator_1",
    )

    with pytest.raises(InvalidActionStateTransitionError) as exc_info:
        transition_action_status(action, ActionStatus.EXECUTED)

    assert "Cannot transition action from 'PROPOSED' to 'EXECUTED'" in str(exc_info.value)

