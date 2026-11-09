"""Unit tests for Action Policy Engine, RBAC gating, and AI Identity blocking."""

import uuid
from datetime import UTC, datetime, timedelta
import pytest

from app.actions.policy import (
    ActionApprovalExpiredError,
    ActionPolicyEngine,
    ActionPolicyViolationError,
    AIApprovalForbiddenError,
    SeparationOfDutiesError,
)
from app.models.action import Action
from app.models.enums import ActionStatus, ActionType, SeverityLevel
from app.security.auth import AuthUser, UserRole


def test_ai_identity_detection():
    """Verify is_ai_identity detects AI agent usernames and IDs."""
    ai_users = [
        AuthUser(user_id="aegis-investigator-01", username="aegis_agent", role=UserRole.ADMIN),
        AuthUser(user_id="usr-123", username="llm_assistant", role=UserRole.OPERATOR),
        AuthUser(user_id="ai_bot_42", username="bot_ops", role=UserRole.ADMIN),
        AuthUser(user_id="usr-ops", username="investigator_ai", role=UserRole.OPERATOR),
    ]
    for u in ai_users:
        assert ActionPolicyEngine.is_ai_identity(u) is True

    human_users = [
        AuthUser(user_id="usr-oper-01", username="alice_ops", role=UserRole.OPERATOR),
        AuthUser(user_id="usr-admin-01", username="bob_admin", role=UserRole.ADMIN),
        AuthUser(user_id="usr-analyst-01", username="charlie_analyst", role=UserRole.ANALYST),
    ]
    for u in human_users:
        assert ActionPolicyEngine.is_ai_identity(u) is False


def test_ai_cannot_approve_or_execute_actions():
    """Verify AI identities are strictly blocked with AIApprovalForbiddenError."""
    ai_user = AuthUser(user_id="aegis-investigator", username="aegis_ai", role=UserRole.ADMIN)

    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Restart service",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting",
        risk_level=SeverityLevel.MEDIUM,
        status=ActionStatus.PENDING_APPROVAL,
        requested_by="alice_ops",
    )

    with pytest.raises(AIApprovalForbiddenError):
        ActionPolicyEngine.validate_can_approve(ai_user, action)

    with pytest.raises(AIApprovalForbiddenError):
        ActionPolicyEngine.validate_can_execute(ai_user, action)


def test_rbac_approval_permissions():
    """Verify approval role gating: VIEWER/ANALYST cannot approve, OPERATOR/ADMIN can."""
    viewer = AuthUser(user_id="u1", username="viewer_user", role=UserRole.VIEWER)
    analyst = AuthUser(user_id="u2", username="analyst_user", role=UserRole.ANALYST)
    operator = AuthUser(user_id="u3", username="operator_user", role=UserRole.OPERATOR)
    admin = AuthUser(user_id="u4", username="admin_user", role=UserRole.ADMIN)

    low_action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Clear Cache",
        action_type=ActionType.CLEAR_CACHE,
        description="Clear cache",
        risk_level=SeverityLevel.LOW,
        status=ActionStatus.PENDING_APPROVAL,
        requested_by="alice_ops",
    )

    high_action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Rollback Deployment",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        description="Rollback",
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.PENDING_APPROVAL,
        requested_by="alice_ops",
    )

    # Viewer cannot approve anything
    with pytest.raises(ActionPolicyViolationError):
        ActionPolicyEngine.validate_can_approve(viewer, low_action)

    # Analyst cannot approve high risk
    with pytest.raises(ActionPolicyViolationError):
        ActionPolicyEngine.validate_can_approve(analyst, high_action)

    # Operator can approve high risk
    ActionPolicyEngine.validate_can_approve(operator, high_action)

    # Admin can approve high risk
    ActionPolicyEngine.validate_can_approve(admin, high_action)


def test_rbac_execution_permissions():
    """Verify execution role gating: only OPERATOR and ADMIN can execute."""
    viewer = AuthUser(user_id="u1", username="viewer_user", role=UserRole.VIEWER)
    analyst = AuthUser(user_id="u2", username="analyst_user", role=UserRole.ANALYST)
    operator = AuthUser(user_id="u3", username="operator_user", role=UserRole.OPERATOR)

    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Restart service",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting",
        risk_level=SeverityLevel.LOW,
        status=ActionStatus.APPROVED,
        requested_by="alice_ops",
        approved_by="operator_user",
    )

    with pytest.raises(ActionPolicyViolationError):
        ActionPolicyEngine.validate_can_execute(viewer, action)

    with pytest.raises(ActionPolicyViolationError):
        ActionPolicyEngine.validate_can_execute(analyst, action)

    ActionPolicyEngine.validate_can_execute(operator, action)


def test_separation_of_duties_enforcement(monkeypatch):
    """Verify requester cannot approve their own action when separation is enabled."""
    from unittest.mock import MagicMock
    import app.actions.policy as policy_module

    mock_settings = MagicMock()
    mock_settings.ENFORCE_SEPARATION_OF_DUTIES = True
    monkeypatch.setattr(policy_module, "get_settings", lambda: mock_settings)

    operator = AuthUser(user_id="u3", username="operator_user", role=UserRole.OPERATOR)

    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Restart service",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting",
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.PENDING_APPROVAL,
        requested_by="operator_user",  # Same user
    )

    with pytest.raises(SeparationOfDutiesError):
        ActionPolicyEngine.validate_can_approve(operator, action)


def test_expired_approval_blocks_execution():
    """Verify expired action is blocked from execution."""
    operator = AuthUser(user_id="u3", username="operator_user", role=UserRole.OPERATOR)

    action = Action(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        title="Restart service",
        action_type=ActionType.RESTART_SERVICE,
        description="Restarting",
        risk_level=SeverityLevel.LOW,
        status=ActionStatus.APPROVED,
        requested_by="alice_ops",
        approved_by="bob_admin",
        expires_at=datetime.now(UTC) - timedelta(minutes=5),  # Expired
    )

    with pytest.raises(ActionApprovalExpiredError):
        ActionPolicyEngine.validate_can_execute(operator, action)

