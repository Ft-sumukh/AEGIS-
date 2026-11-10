"""Operational Actions & Human Approval REST API endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.actions.fingerprint import (
    ActionTamperedError,
    compute_action_fingerprint,
    verify_action_fingerprint,
)
from app.actions.infrastructure import (
    ActionExecutionResult,
    ActionPreconditionFailedError,
    SimulatedExecutor,
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
)
from app.actions.state_machine import (
    InvalidActionStateTransitionError,
    transition_action_status,
)
from app.actions.verification import (
    VerificationResult,
    VerificationService,
)
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.action import Action, ActionApproval
from app.models.enums import (
    ActionApprovalDecision,
    ActionStatus,
    ActionType,
    AuditActorType,
    SeverityLevel,
)
from app.models.incident import Incident
from app.models.recommendation import Recommendation
from app.schemas.action import (
    ActionApprovalRequest,
    ActionCreate,
    ActionDetailRead,
    ActionExecutionRequest,
    ActionListResponse,
    ActionRead,
    ActionRejectionRequest,
    ActionSubmitRequest,
)
from app.security.audit import SecurityAuditService
from app.security.auth import AuthUser, UserRole, get_current_user, require_role

logger = get_logger("aegis.api.actions")
router = APIRouter(prefix="/actions", tags=["Operational Actions & Approval Engine"])


@router.get(
    "/registry/definitions",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List supported operational action definitions",
    description="Returns definitions, required roles, risk classifications, and preconditions for all registered action types.",
)
def list_action_definitions(
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Returns catalog of registered action definitions."""
    defs = ActionRegistry.list_definitions()
    return [
        {
            "action_type": d.action_type.value,
            "name": d.name,
            "description": d.description,
            "risk_level": d.risk_level.value,
            "required_role": d.required_role.value,
            "requires_approval": d.requires_approval,
            "preconditions": d.preconditions,
            "potential_downside": d.potential_downside,
            "expected_outcome": d.expected_outcome,
        }
        for d in defs
    ]


@router.get(
    "",
    response_model=ActionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List operational action proposals",
    description="Returns filtered and paginated operational action proposals across incidents.",
)
def list_actions(
    status_filter: ActionStatus | None = Query(default=None, alias="status", description="Filter by action status"),
    action_type: ActionType | None = Query(default=None, description="Filter by action type"),
    incident_id: uuid.UUID | None = Query(default=None, description="Filter by incident ID"),
    risk_level: SeverityLevel | None = Query(default=None, description="Filter by risk level"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionListResponse:
    """Lists operational actions with optional filters."""
    query = select(Action)
    count_query = select(func.count(Action.id))

    if status_filter:
        query = query.where(Action.status == status_filter)
        count_query = count_query.where(Action.status == status_filter)

    if action_type:
        query = query.where(Action.action_type == action_type)
        count_query = count_query.where(Action.action_type == action_type)

    if incident_id:
        query = query.where(Action.incident_id == incident_id)
        count_query = count_query.where(Action.incident_id == incident_id)

    if risk_level:
        query = query.where(Action.risk_level == risk_level)
        count_query = count_query.where(Action.risk_level == risk_level)

    total = db.scalar(count_query) or 0
    actions = db.scalars(
        query.order_by(Action.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return ActionListResponse(
        items=[ActionRead.model_validate(a) for a in actions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/incidents/{incident_id}",
    response_model=ActionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Propose an operational action for an incident",
    description="Creates a new action proposal linked to an incident recommendation with typed parameters and SHA-256 fingerprint.",
)
def propose_action(
    incident_id: uuid.UUID,
    payload: ActionCreate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionRead:
    """Proposes a new operational action."""
    ActionPolicyEngine.validate_can_propose(user, payload.action_type)

    # 1. Verify incident exists
    incident = db.scalar(select(Incident).where(Incident.id == incident_id))
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")

    # 2. Verify recommendation exists
    rec = db.scalar(select(Recommendation).where(Recommendation.id == payload.recommendation_id))
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recommendation '{payload.recommendation_id}' not found.")

    # 3. Check idempotency key if provided
    if payload.idempotency_key:
        existing = db.scalar(select(Action).where(Action.idempotency_key == payload.idempotency_key))
        if existing:
            return ActionRead.model_validate(existing)

    # 4. Validate parameters against ActionRegistry
    try:
        validated_params = ActionRegistry.validate_parameters(payload.action_type, payload.parameters)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid action parameters: {err}")

    definition = ActionRegistry.get_definition(payload.action_type)
    target_service = payload.target_service or validated_params.get("service") or (incident.affected_systems[0] if incident.affected_systems else None)
    risk_level = payload.risk_level or definition.risk_level
    title = payload.title or f"{definition.name}: {target_service or 'System'}"
    description = payload.description or rec.description

    # 5. Compute security fingerprint
    fingerprint = compute_action_fingerprint(
        action_type=payload.action_type,
        target_service=target_service,
        parameters=validated_params,
        risk_level=risk_level,
    )

    action = Action(
        id=uuid.uuid4(),
        incident_id=incident_id,
        recommendation_id=payload.recommendation_id,
        title=title,
        action_type=payload.action_type,
        description=description,
        risk_level=risk_level,
        status=ActionStatus.PROPOSED,
        target_service=target_service,
        parameters=validated_params,
        preconditions=definition.preconditions,
        expected_outcome=definition.expected_outcome,
        verification_strategy=definition.verification_strategy,
        fingerprint=fingerprint,
        idempotency_key=payload.idempotency_key,
        requested_by=user.username,
        requested_at=datetime.now(UTC),
        action_metadata={"actor_role": user.role.value, "downside": definition.potential_downside},
    )

    db.add(action)
    db.flush()

    # Record Audit Event
    SecurityAuditService.record_event(
        db=db,
        action="ACTION_PROPOSED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=incident.company_id,
        metadata={
            "action_type": action.action_type.value,
            "target_service": target_service,
            "risk_level": risk_level.value,
            "fingerprint": fingerprint,
        },
    )
    db.commit()
    db.refresh(action)

    return ActionRead.model_validate(action)


@router.get(
    "/{action_id}",
    response_model=ActionRead,
    status_code=status.HTTP_200_OK,
    summary="Get operational action details",
    description="Returns comprehensive details of an action proposal, its approval trail, execution state, and verification metrics.",
)
def get_action(
    action_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionRead:
    """Retrieves single action proposal by ID."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")
    return ActionRead.model_validate(action)


@router.post(
    "/{action_id}/submit",
    response_model=ActionRead,
    status_code=status.HTTP_200_OK,
    summary="Submit action proposal for human authorization",
    description="Transitions an action from PROPOSED to PENDING_APPROVAL and updates security fingerprint.",
)
def submit_action(
    action_id: uuid.UUID,
    payload: ActionSubmitRequest = ActionSubmitRequest(),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionRead:
    """Submits action proposal for human authorization."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")

    ActionPolicyEngine.validate_can_propose(user, action.action_type)

    try:
        transition_action_status(action, ActionStatus.PENDING_APPROVAL, reason=payload.notes)
    except InvalidActionStateTransitionError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # Refresh canonical fingerprint
    action.fingerprint = compute_action_fingerprint(
        action_type=action.action_type,
        target_service=action.target_service,
        parameters=action.parameters,
        risk_level=action.risk_level,
    )

    company_id = action.incident.company_id if action.incident else None
    SecurityAuditService.record_event(
        db=db,
        action="APPROVAL_REQUESTED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        metadata={"fingerprint": action.fingerprint, "notes": payload.notes},
    )
    db.commit()
    db.refresh(action)

    return ActionRead.model_validate(action)


@router.post(
    "/{action_id}/approve",
    response_model=ActionRead,
    status_code=status.HTTP_200_OK,
    summary="Authorize operational action proposal",
    description="Explicit human operator authorization. Verifies parameter fingerprint, role gating, expiration, and records approval audit trail.",
)
def approve_action(
    action_id: uuid.UUID,
    payload: ActionApprovalRequest = ActionApprovalRequest(),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionRead:
    """Authorizes an action proposal."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")

    # 1. If still in PROPOSED, automatically progress to PENDING_APPROVAL first
    if action.status == ActionStatus.PROPOSED:
        transition_action_status(action, ActionStatus.PENDING_APPROVAL)

    # 2. Enforce Human Authorization Policy & Role Gating (AI explicitly blocked!)
    try:
        ActionPolicyEngine.validate_can_approve(user, action)
    except AIApprovalForbiddenError as err:
        company_id = action.incident.company_id if action.incident else None
        SecurityAuditService.record_event(
            db=db,
            action="AI_APPROVAL_BLOCKED",
            actor_id=user.username,
            actor_type=AuditActorType.AGENT,
            resource_type="action",
            resource_id=str(action.id),
            company_id=company_id,
            result="BLOCKED",
            reason=str(err),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ActionPolicyViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    # 3. For HIGH/CRITICAL actions, enforce explicit typed confirmation phrase
    if action.risk_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
        expected_phrase = f"APPROVE {action.action_type.value.replace('_', ' ')}".upper()
        if not payload.confirmation_phrase or payload.confirmation_phrase.strip().upper() != expected_phrase:
            # Also accept "APPROVE" or "CONFIRM" as alternative valid confirmations
            alt_acceptable = ("APPROVE", "CONFIRM", f"APPROVE {action.action_type.value}")
            if not payload.confirmation_phrase or payload.confirmation_phrase.strip().upper() not in alt_acceptable:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Typed confirmation required for {action.risk_level} action. Please confirm with '{expected_phrase}'.",
                )

    # 4. Verify parameter fingerprint immutability
    current_fingerprint = compute_action_fingerprint(
        action_type=action.action_type,
        target_service=action.target_service,
        parameters=action.parameters,
        risk_level=action.risk_level,
    )
    action.fingerprint = current_fingerprint

    # 5. Transition to APPROVED
    try:
        transition_action_status(action, ActionStatus.APPROVED, reason=payload.reason)
    except InvalidActionStateTransitionError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    now = datetime.now(UTC)
    action.approved_by = user.username
    action.approved_at = now
    action.expires_at = ActionPolicyEngine.calculate_expiration(now)

    # 6. Record immutable ActionApproval entity
    approval_entry = ActionApproval(
        id=uuid.uuid4(),
        action_id=action.id,
        decision=ActionApprovalDecision.APPROVED,
        decision_by=user.username,
        decision_at=now,
        reason=payload.reason,
        fingerprint_verified=current_fingerprint,
        approval_metadata={"actor_role": user.role.value, "confirmation": payload.confirmation_phrase},
    )
    db.add(approval_entry)

    # 7. Audit log event
    company_id = action.incident.company_id if action.incident else None
    SecurityAuditService.record_event(
        db=db,
        action="ACTION_APPROVED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        metadata={
            "fingerprint": current_fingerprint,
            "expires_at": action.expires_at.isoformat(),
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(action)

    return ActionRead.model_validate(action)


@router.post(
    "/{action_id}/reject",
    response_model=ActionRead,
    status_code=status.HTTP_200_OK,
    summary="Reject operational action proposal",
    description="Explicit human rejection of an action proposal with mandatory justification.",
)
def reject_action(
    action_id: uuid.UUID,
    payload: ActionRejectionRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionRead:
    """Rejects an action proposal."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")

    if ActionPolicyEngine.is_ai_identity(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI agents cannot reject actions. Decisions must come from authenticated humans.",
        )

    if user.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot reject actions.")

    try:
        transition_action_status(action, ActionStatus.REJECTED, reason=payload.reason)
    except InvalidActionStateTransitionError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    now = datetime.now(UTC)
    action.failure_reason = payload.reason

    current_fingerprint = compute_action_fingerprint(
        action_type=action.action_type,
        target_service=action.target_service,
        parameters=action.parameters,
        risk_level=action.risk_level,
    )

    approval_entry = ActionApproval(
        id=uuid.uuid4(),
        action_id=action.id,
        decision=ActionApprovalDecision.REJECTED,
        decision_by=user.username,
        decision_at=now,
        reason=payload.reason,
        fingerprint_verified=current_fingerprint,
        approval_metadata={"actor_role": user.role.value},
    )
    db.add(approval_entry)

    company_id = action.incident.company_id if action.incident else None
    SecurityAuditService.record_event(
        db=db,
        action="ACTION_REJECTED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        result="REJECTED",
        reason=payload.reason,
        metadata={"fingerprint": current_fingerprint},
    )
    db.commit()
    db.refresh(action)

    return ActionRead.model_validate(action)


@router.post(
    "/{action_id}/execute",
    response_model=ActionExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Execute an approved operational action",
    description="Validates authorization, checks parameter fingerprint immutability and preconditions, and executes against simulated infrastructure.",
)
def execute_action(
    action_id: uuid.UUID,
    payload: ActionExecutionRequest = ActionExecutionRequest(),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionExecutionResult:
    """Executes an authorized operational action."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")

    company_id = action.incident.company_id if action.incident else None

    # 1. Validate Execution Policy & Gating (AI strictly blocked!)
    try:
        ActionPolicyEngine.validate_can_execute(user, action)
    except ActionApprovalExpiredError as err:
        transition_action_status(action, ActionStatus.EXPIRED, reason=str(err))
        SecurityAuditService.record_event(
            db=db,
            action="ACTION_EXPIRED",
            actor_id=user.username,
            actor_type=AuditActorType.SYSTEM,
            resource_type="action",
            resource_id=str(action.id),
            company_id=company_id,
            result="EXPIRED",
            reason=str(err),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except (AIApprovalForbiddenError, ActionPolicyViolationError) as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    # 2. Immutability Verification: Recompute and match fingerprint
    is_valid_fingerprint = verify_action_fingerprint(
        action_type=action.action_type,
        target_service=action.target_service,
        parameters=action.parameters,
        risk_level=action.risk_level,
        expected_fingerprint=action.fingerprint,
    )
    if not is_valid_fingerprint:
        # Parameter Tamper Alert!
        SecurityAuditService.record_event(
            db=db,
            action="ACTION_TAMPER_DETECTED",
            actor_id=user.username,
            actor_type=AuditActorType.USER,
            resource_type="action",
            resource_id=str(action.id),
            company_id=company_id,
            result="BLOCKED",
            reason="Action parameters or target were modified after approval was granted.",
            metadata={"expected_fingerprint": action.fingerprint},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EXECUTION BLOCKED: Action parameters have been altered since approval was granted. Fingerprint mismatch.",
        )

    # 3. Concurrency Protection
    try:
        ActionPolicyEngine.check_target_concurrency(db, action.target_service, exclude_action_id=action.id)
    except ConcurrentActionConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))

    # 4. Dry-Run Execution
    if payload.dry_run:
        try:
            return SimulatedExecutor.execute(db, action, dry_run=True)
        except ActionPreconditionFailedError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # 5. Live Simulated Execution
    now = datetime.now(UTC)
    action.started_at = now
    transition_action_status(action, ActionStatus.EXECUTING)
    db.flush()

    SecurityAuditService.record_event(
        db=db,
        action="EXECUTION_STARTED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        metadata={"action_type": action.action_type.value, "target": action.target_service},
    )

    try:
        result = SimulatedExecutor.execute(db, action, dry_run=False)
        action.completed_at = datetime.now(UTC)
        action.executed_at = now
        action.execution_result = result.message
        transition_action_status(action, ActionStatus.EXECUTED)

        SecurityAuditService.record_event(
            db=db,
            action="EXECUTION_COMPLETED",
            actor_id=user.username,
            actor_type=AuditActorType.USER,
            resource_type="action",
            resource_id=str(action.id),
            company_id=company_id,
            metadata={"duration_ms": result.duration_ms, "result": result.message},
        )
        db.commit()
        db.refresh(action)
        return result

    except Exception as err:
        action.completed_at = datetime.now(UTC)
        action.failure_reason = str(err)
        transition_action_status(action, ActionStatus.FAILED, reason=str(err))

        SecurityAuditService.record_event(
            db=db,
            action="EXECUTION_FAILED",
            actor_id=user.username,
            actor_type=AuditActorType.USER,
            resource_type="action",
            resource_id=str(action.id),
            company_id=company_id,
            result="FAILED",
            reason=str(err),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Execution failed: {err}")


@router.post(
    "/{action_id}/verify",
    response_model=VerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Verify operational recovery following action execution",
    description="Collects post-action telemetry, compares against baselines, and determines whether intended recovery occurred.",
)
def verify_action(
    action_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerificationResult:
    """Verifies operational recovery following action execution."""
    action = db.scalar(select(Action).where(Action.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")

    if action.status not in (ActionStatus.EXECUTED, ActionStatus.VERIFYING, ActionStatus.VERIFIED, ActionStatus.VERIFICATION_FAILED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify action in status '{action.status}'. Must be EXECUTED.",
        )

    company_id = action.incident.company_id if action.incident else None
    SecurityAuditService.record_event(
        db=db,
        action="VERIFICATION_STARTED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        metadata={"strategy": action.verification_strategy},
    )

    result = VerificationService.verify(db, action)

    SecurityAuditService.record_event(
        db=db,
        action="VERIFICATION_COMPLETED" if result.outcome.startswith("VERIFIED") else "VERIFICATION_FAILED",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type="action",
        resource_id=str(action.id),
        company_id=company_id,
        result=result.outcome.value,
        reason=result.summary,
        metadata={
            "signals_verified": result.signals_verified,
            "signals_failed": result.signals_failed,
            "metrics_after": result.metrics_after,
        },
    )
    db.commit()
    db.refresh(action)

    return result


@router.get(
    "/{action_id}/dry-run",
    response_model=ActionExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Execute dry-run simulation validation on action proposal",
    description="Simulates action execution without changing infrastructure state to test permissions and preconditions.",
)
def dry_run_action(
    action_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionExecutionResult:
    """Dry-run execution validation."""
    return execute_action(
        action_id=action_id,
        payload=ActionExecutionRequest(dry_run=True),
        user=user,
        db=db,
    )
