"""Aegis Action & Human Approval Engine package."""

from app.actions.fingerprint import (
    ActionTamperedError,
    compute_action_fingerprint,
    verify_action_fingerprint,
)
from app.actions.infrastructure import (
    ActionExecutionResult,
    ActionPreconditionFailedError,
    SimulatedExecutor,
    SimulatedInfrastructure,
)
from app.actions.policy import (
    AIApprovalForbiddenError,
    ActionApprovalExpiredError,
    ActionPolicyEngine,
    ActionPolicyViolationError,
    ConcurrentActionConflictError,
    SeparationOfDutiesError,
)
from app.actions.registry import (
    ActionDefinition,
    ActionRegistry,
    ClearCacheParameters,
    FeatureFlagParameters,
    RestartServiceParameters,
    RollbackDeploymentParameters,
    ScaleServiceParameters,
    TrafficParameters,
)
from app.actions.state_machine import (
    InvalidActionStateTransitionError,
    can_transition,
    transition_action_status,
)
from app.actions.verification import (
    VerificationResult,
    VerificationService,
)

__all__ = [
    "AIApprovalForbiddenError",
    "ActionApprovalExpiredError",
    "ActionDefinition",
    "ActionExecutionResult",
    "ActionPolicyEngine",
    "ActionPolicyViolationError",
    "ActionPreconditionFailedError",
    "ActionRegistry",
    "ActionTamperedError",
    "ClearCacheParameters",
    "ConcurrentActionConflictError",
    "FeatureFlagParameters",
    "InvalidActionStateTransitionError",
    "RestartServiceParameters",
    "RollbackDeploymentParameters",
    "ScaleServiceParameters",
    "SeparationOfDutiesError",
    "SimulatedExecutor",
    "SimulatedInfrastructure",
    "TrafficParameters",
    "VerificationResult",
    "VerificationService",
    "can_transition",
    "compute_action_fingerprint",
    "transition_action_status",
    "verify_action_fingerprint",
]
