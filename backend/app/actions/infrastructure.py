"""Simulated infrastructure state and safe action execution engine."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.models.enums import (
    ActionStatus,
    ActionType,
    DeploymentStatus,
    SeverityLevel,
)
from app.models.events import Deployment, SystemEvent
from app.models.metrics import OperationalMetric

logger = get_logger("aegis.actions.infrastructure")


class ActionPreconditionFailedError(Exception):
    """Raised when an action's operational preconditions are not satisfied."""
    pass


class ActionExecutionResult(BaseModel):
    """Structured result returned by an action executor."""
    model_config = ConfigDict(extra="ignore")

    success: bool
    execution_id: str
    action_id: str
    started_at: str
    completed_at: str
    duration_ms: float
    dry_run: bool
    message: str
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    emitted_events: list[dict[str, Any]] = []
    error: str | None = None


class SimulatedInfrastructure:
    """In-memory simulated infrastructure state for safe, synthetic operational actions."""

    _instance: "SimulatedInfrastructure | None" = None

    def __init__(self) -> None:
        self.services: dict[str, dict[str, Any]] = {}
        self.feature_flags: dict[str, bool] = {}
        self.reset()

    @classmethod
    def get_instance(cls) -> "SimulatedInfrastructure":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset(self) -> None:
        """Resets simulated infrastructure state to initial incident scenario state."""
        self.services = {
            "checkout-service": {
                "active_deployment": "v4.8.2",
                "previous_stable_deployment": "v4.8.1",
                "desired_capacity": 4,
                "actual_capacity": 4,
                "traffic_state": "ACTIVE",
                "health_state": "CRITICAL",
                "cache_tier_flushed": False,
            },
            "catalog-service": {
                "active_deployment": "v2.1.0",
                "previous_stable_deployment": "v2.0.8",
                "desired_capacity": 3,
                "actual_capacity": 3,
                "traffic_state": "ACTIVE",
                "health_state": "HEALTHY",
                "cache_tier_flushed": False,
            },
            "auth-service": {
                "active_deployment": "v3.0.4",
                "previous_stable_deployment": "v3.0.2",
                "desired_capacity": 2,
                "actual_capacity": 2,
                "traffic_state": "ACTIVE",
                "health_state": "HEALTHY",
                "cache_tier_flushed": False,
            },
            "payment-gateway": {
                "active_deployment": "v1.9.0",
                "previous_stable_deployment": "v1.8.5",
                "desired_capacity": 2,
                "actual_capacity": 2,
                "traffic_state": "ACTIVE",
                "health_state": "DEGRADED",
                "cache_tier_flushed": False,
            },
            "postgres-cluster": {
                "active_deployment": "16.2",
                "desired_capacity": 1,
                "actual_capacity": 1,
                "traffic_state": "ACTIVE",
                "health_state": "DEGRADED",
                "cache_tier_flushed": False,
            },
        }
        self.feature_flags = {
            "checkout_v2_optimization": True,
            "express_checkout": True,
            "rate_limiter_strict_mode": False,
            "async_order_processing": False,
        }

    def get_service_state(self, service_name: str) -> dict[str, Any]:
        """Retrieves current simulated state for a service."""
        return self.services.get(service_name, {
            "active_deployment": "v1.0.0",
            "desired_capacity": 2,
            "actual_capacity": 2,
            "traffic_state": "ACTIVE",
            "health_state": "HEALTHY",
        })


class SimulatedExecutor:
    """Executes validated operational actions against simulated infrastructure."""

    @classmethod
    def validate_preconditions(
        cls,
        db: Session,
        action_type: ActionType,
        target_service: str | None,
        parameters: dict[str, Any],
    ) -> None:
        """Validates action preconditions immediately before execution."""
        infra = SimulatedInfrastructure.get_instance()

        if target_service:
            if target_service not in infra.services:
                raise ActionPreconditionFailedError(
                    f"Precondition Failed: Target service '{target_service}' is not registered in infrastructure topology."
                )

        if action_type == ActionType.ROLLBACK_DEPLOYMENT:
            target_version = parameters.get("target_version")
            if not target_version:
                raise ActionPreconditionFailedError("Precondition Failed: 'target_version' parameter is required for rollback.")
            current_state = infra.get_service_state(target_service or "")
            if current_state.get("active_deployment") == target_version:
                raise ActionPreconditionFailedError(
                    f"Precondition Failed: Target version '{target_version}' is already the currently active deployment."
                )

        elif action_type == ActionType.SCALE_SERVICE:
            target_cap = parameters.get("target_capacity")
            if target_cap is None or target_cap < 1 or target_cap > 50:
                raise ActionPreconditionFailedError(
                    f"Precondition Failed: Target capacity '{target_cap}' must be between 1 and 50."
                )

        elif action_type in (ActionType.ENABLE_FEATURE_FLAG, ActionType.DISABLE_FEATURE_FLAG):
            flag_name = parameters.get("flag_name")
            if not flag_name or flag_name not in infra.feature_flags:
                raise ActionPreconditionFailedError(
                    f"Precondition Failed: Feature flag '{flag_name}' is not recognized."
                )

    @classmethod
    def execute(
        cls,
        db: Session,
        action: Any,  # Action model instance
        dry_run: bool = False,
    ) -> ActionExecutionResult:
        """Executes an authorized action proposal against simulated infrastructure."""
        settings = get_settings()
        if settings.ACTION_EXECUTION_MODE != "SIMULATED":
            raise ValueError(
                f"Unsupported execution mode '{settings.ACTION_EXECUTION_MODE}'. "
                "Aegis is strictly configured to execute in 'SIMULATED' mode to protect real cloud infrastructure."
            )

        start_time = time.perf_counter()
        started_at = datetime.now(UTC)
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        infra = SimulatedInfrastructure.get_instance()

        target = action.target_service or ""
        state_before = dict(infra.get_service_state(target))
        emitted_events: list[dict[str, Any]] = []

        # 1. Precondition checks
        cls.validate_preconditions(
            db=db,
            action_type=action.action_type,
            target_service=action.target_service,
            parameters=action.parameters,
        )

        # 2. Dry-Run Handling
        if dry_run:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ActionExecutionResult(
                success=True,
                execution_id=f"dry-{execution_id}",
                action_id=str(action.id),
                started_at=started_at.isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
                duration_ms=duration_ms,
                dry_run=True,
                message=f"Dry-run simulation passed: Action '{action.action_type}' can be safely executed against '{target}'.",
                state_before=state_before,
                state_after=state_before,
                emitted_events=[],
            )

        # 3. Simulated Execution Mutations
        message = ""
        company_id = action.incident.company_id if action.incident else None

        if action.action_type == ActionType.ROLLBACK_DEPLOYMENT:
            target_version = action.parameters.get("target_version", "v4.8.1")
            prev_version = state_before.get("active_deployment", "v4.8.2")

            # Update simulated infrastructure
            infra.services[target]["active_deployment"] = target_version
            infra.services[target]["health_state"] = "HEALTHY"

            # Create Deployment entity record
            if company_id:
                dep_record = Deployment(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    service=target,
                    environment="production",
                    version=target_version,
                    status=DeploymentStatus.ROLLED_BACK,
                    deployed_by=f"aegis-approved:{action.approved_by}",
                    deployed_at=datetime.now(UTC),
                    deployment_metadata={
                        "action_id": str(action.id),
                        "rollback_from": prev_version,
                        "reason": "Automated operational rollback following incident mitigation approval",
                    },
                )
                db.add(dep_record)

            # Emit technical SystemEvent
            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="DEPLOYMENT_ROLLBACK",
                    severity=SeverityLevel.INFO,
                    service=target,
                    environment="production",
                    message=f"Production rollback of {target} from {prev_version} to {target_version} completed.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"action_id": str(action.id), "version": target_version},
                )
                db.add(sys_evt)
                emitted_events.append({"event_type": "DEPLOYMENT_ROLLBACK", "version": target_version})

            # Inject post-mitigation recovered telemetry metrics
            if company_id:
                now_ts = datetime.now(UTC)
                recovered_metrics = [
                    OperationalMetric(
                        id=uuid.uuid4(),
                        company_id=company_id,
                        metric_name="api_error_rate",
                        value=0.85,
                        unit="percent",
                        source="api-gateway",
                        timestamp=now_ts,
                        dimension_data={"service": target, "route": "/checkout"},
                    ),
                    OperationalMetric(
                        id=uuid.uuid4(),
                        company_id=company_id,
                        metric_name="api_latency_p95",
                        value=175.0,
                        unit="ms",
                        source="api-gateway",
                        timestamp=now_ts,
                        dimension_data={"service": target, "route": "/checkout"},
                    ),
                    OperationalMetric(
                        id=uuid.uuid4(),
                        company_id=company_id,
                        metric_name="checkout_failure_rate",
                        value=1.1,
                        unit="percent",
                        source="checkout-service",
                        timestamp=now_ts,
                        dimension_data={"service": target},
                    ),
                ]
                db.add_all(recovered_metrics)

            message = f"Rolled back {target} from {prev_version} to {target_version}. Service health restored to HEALTHY."

        elif action.action_type == ActionType.RESTART_SERVICE:
            infra.services[target]["health_state"] = "HEALTHY"
            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="SERVICE_RESTART",
                    severity=SeverityLevel.INFO,
                    service=target,
                    environment="production",
                    message=f"Rolling restart of {target} completed. Connection pools recycled.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"action_id": str(action.id)},
                )
                db.add(sys_evt)
                emitted_events.append({"event_type": "SERVICE_RESTART", "service": target})

            message = f"Restarted service {target}. Replicas recycled and connection pools refreshed."

        elif action.action_type == ActionType.SCALE_SERVICE:
            target_cap = int(action.parameters["target_capacity"])
            prev_cap = infra.services[target].get("actual_capacity", 2)
            infra.services[target]["desired_capacity"] = target_cap
            infra.services[target]["actual_capacity"] = target_cap

            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="CAPACITY_SCALE",
                    severity=SeverityLevel.INFO,
                    service=target,
                    environment="production",
                    message=f"Scaled {target} capacity from {prev_cap} to {target_cap} replicas.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"action_id": str(action.id), "capacity": target_cap},
                )
                db.add(sys_evt)
                emitted_events.append({"event_type": "CAPACITY_SCALE", "capacity": target_cap})

            message = f"Scaled {target} capacity to {target_cap} replicas."

        elif action.action_type in (ActionType.ENABLE_FEATURE_FLAG, ActionType.DISABLE_FEATURE_FLAG):
            flag_name = action.parameters["flag_name"]
            is_enable = action.action_type == ActionType.ENABLE_FEATURE_FLAG
            infra.feature_flags[flag_name] = is_enable

            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="FEATURE_FLAG_UPDATE",
                    severity=SeverityLevel.INFO,
                    service=target or "global",
                    environment="production",
                    message=f"Feature flag '{flag_name}' updated to {is_enable}.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"flag_name": flag_name, "enabled": is_enable},
                )
                db.add(sys_evt)
                emitted_events.append({"flag_name": flag_name, "enabled": is_enable})

            message = f"Feature flag '{flag_name}' set to {is_enable}."

        elif action.action_type == ActionType.CLEAR_CACHE:
            cache_tier = action.parameters.get("cache_tier", "redis_l2")
            infra.services[target]["cache_tier_flushed"] = True

            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="CACHE_PURGED",
                    severity=SeverityLevel.INFO,
                    service=target,
                    environment="production",
                    message=f"Purged {cache_tier} for service {target}.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"cache_tier": cache_tier},
                )
                db.add(sys_evt)
                emitted_events.append({"cache_tier": cache_tier})

            message = f"Flushed {cache_tier} cache on {target}."

        elif action.action_type in (ActionType.PAUSE_TRAFFIC, ActionType.RESUME_TRAFFIC):
            is_pause = action.action_type == ActionType.PAUSE_TRAFFIC
            traffic_state = "PAUSED" if is_pause else "ACTIVE"
            infra.services[target]["traffic_state"] = traffic_state

            if company_id:
                sys_evt = SystemEvent(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    event_type="TRAFFIC_ROUTING_CHANGE",
                    severity=SeverityLevel.WARNING if is_pause else SeverityLevel.INFO,
                    service=target,
                    environment="production",
                    message=f"Ingress traffic routing for {target} changed to {traffic_state}.",
                    timestamp=datetime.now(UTC),
                    event_metadata={"traffic_state": traffic_state},
                )
                db.add(sys_evt)
                emitted_events.append({"traffic_state": traffic_state})

            message = f"Ingress traffic for {target} transitioned to {traffic_state}."

        else:
            message = f"Simulated action '{action.action_type}' executed successfully."

        state_after = dict(infra.get_service_state(target))
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ActionExecutionResult(
            success=True,
            execution_id=execution_id,
            action_id=str(action.id),
            started_at=started_at.isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            duration_ms=duration_ms,
            dry_run=False,
            message=message,
            state_before=state_before,
            state_after=state_after,
            emitted_events=emitted_events,
        )
