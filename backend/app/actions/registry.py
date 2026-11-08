"""Action registry, typed parameter schemas, and operational definitions."""

from typing import Any, Type

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActionType, SeverityLevel
from app.security.auth import UserRole


# ---------------------------------------------------------------------------
# Typed Action Parameter Schemas
# ---------------------------------------------------------------------------

class RollbackDeploymentParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, max_length=100, description="Target microservice name")
    target_version: str = Field(..., min_length=1, max_length=50, description="Image tag or release version to roll back to")
    current_version: str | None = Field(default=None, max_length=50, description="Currently deployed active version")
    environment: str = Field(default="production", max_length=50, description="Target deployment environment")


class RestartServiceParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, max_length=100, description="Target microservice name")
    grace_period_seconds: int = Field(default=10, ge=0, le=300, description="Graceful shutdown drain duration")


class ScaleServiceParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, max_length=100, description="Target microservice name")
    target_capacity: int = Field(..., ge=1, le=50, description="Desired instance replica count")
    current_capacity: int | None = Field(default=None, ge=1, le=50, description="Current instance replica count")


class FeatureFlagParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag_name: str = Field(..., min_length=1, max_length=100, description="Name of the feature flag")
    enabled: bool = Field(default=True, description="Desired target flag state")
    target_scope: str = Field(default="global", max_length=50, description="Evaluation scope or tenant tier")


class ClearCacheParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, max_length=100, description="Target service cache to flush")
    cache_tier: str = Field(default="redis_l2", max_length=50, description="Target cache tier (redis_l1, redis_l2, local_mem)")


class TrafficParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, max_length=100, description="Target service route")
    action: str = Field(..., pattern="^(PAUSE|RESUME|THROTTLE)$", description="Traffic action: PAUSE, RESUME, or THROTTLE")
    traffic_percentage: int = Field(default=100, ge=0, le=100, description="Permitted percentage of ingress traffic")


class GenericActionParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    service: str | None = Field(default=None, description="Optional target service")


# ---------------------------------------------------------------------------
# Action Definition & Metadata Registry
# ---------------------------------------------------------------------------

class ActionDefinition(BaseModel):
    """Centralized definition of an operational action type."""

    action_type: ActionType
    name: str
    description: str
    risk_level: SeverityLevel
    required_role: UserRole
    requires_approval: bool = True
    parameter_schema: Any  # Type[BaseModel]
    executor_name: str
    verification_strategy: str
    preconditions: list[str]
    potential_downside: str
    expected_outcome: str


class ActionRegistry:
    """Central registry of supported operational actions in Aegis."""

    _definitions: dict[ActionType, ActionDefinition] = {
        ActionType.ROLLBACK_DEPLOYMENT: ActionDefinition(
            action_type=ActionType.ROLLBACK_DEPLOYMENT,
            name="Rollback Deployment",
            description="Reverts target service to a previously verified stable release image tag.",
            risk_level=SeverityLevel.HIGH,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=RollbackDeploymentParameters,
            executor_name="simulated_rollback",
            verification_strategy="rollback_metrics",
            preconditions=[
                "target_service_exists",
                "target_version_exists",
                "service_is_degraded_or_critical",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="Recent code patches, bug fixes, or database schema additions introduced in the current version will be reverted.",
            expected_outcome="Service error rate and latency immediately return toward nominal baseline.",
        ),
        ActionType.RESTART_SERVICE: ActionDefinition(
            action_type=ActionType.RESTART_SERVICE,
            name="Restart Service",
            description="Executes a graceful rolling restart of target service worker replicas.",
            risk_level=SeverityLevel.HIGH,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=RestartServiceParameters,
            executor_name="simulated_restart",
            verification_strategy="restart_health",
            preconditions=[
                "target_service_exists",
                "service_is_degraded_or_critical",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="Transient latency blip and dropped in-flight keepalive connections during pod cycle.",
            expected_outcome="Memory leaks and saturated connection pools are flushed, restoring nominal responsiveness.",
        ),
        ActionType.SCALE_SERVICE: ActionDefinition(
            action_type=ActionType.SCALE_SERVICE,
            name="Scale Service Capacity",
            description="Adjusts worker pod/container replica count to absorb traffic volume.",
            risk_level=SeverityLevel.MEDIUM,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=ScaleServiceParameters,
            executor_name="simulated_scale",
            verification_strategy="scale_capacity",
            preconditions=[
                "target_service_exists",
                "target_capacity_within_bounds",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="Increased downstream database connection pool pressure and higher infrastructure cost.",
            expected_outcome="CPU utilization and request queue depth decrease under distributed load.",
        ),
        ActionType.ENABLE_FEATURE_FLAG: ActionDefinition(
            action_type=ActionType.ENABLE_FEATURE_FLAG,
            name="Enable Feature Flag",
            description="Activates a dynamic operational kill-switch or feature toggle.",
            risk_level=SeverityLevel.MEDIUM,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=FeatureFlagParameters,
            executor_name="simulated_flag",
            verification_strategy="feature_flag_state",
            preconditions=[
                "feature_flag_exists",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="May expose users to newly activated alternate operational code paths.",
            expected_outcome="Target operational mitigation route is dynamically activated.",
        ),
        ActionType.DISABLE_FEATURE_FLAG: ActionDefinition(
            action_type=ActionType.DISABLE_FEATURE_FLAG,
            name="Disable Feature Flag",
            description="Deactivates a dynamic operational feature or optimization path.",
            risk_level=SeverityLevel.MEDIUM,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=FeatureFlagParameters,
            executor_name="simulated_flag",
            verification_strategy="feature_flag_state",
            preconditions=[
                "feature_flag_exists",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="Deactivates dependent features or experimental performance improvements.",
            expected_outcome="Reverts request flow to default baseline code path.",
        ),
        ActionType.CLEAR_CACHE: ActionDefinition(
            action_type=ActionType.CLEAR_CACHE,
            name="Clear Cache",
            description="Purges corrupted or stale cache keys from specified memory cache tier.",
            risk_level=SeverityLevel.LOW,
            required_role=UserRole.OPERATOR,
            requires_approval=True,
            parameter_schema=ClearCacheParameters,
            executor_name="simulated_cache",
            verification_strategy="cache_clear",
            preconditions=[
                "target_service_exists",
                "approval_valid",
            ],
            potential_downside="Temporary cache-stampede spike on primary database backend.",
            expected_outcome="Stale or poisoned cache entries are flushed, requiring fresh queries.",
        ),
        ActionType.PAUSE_TRAFFIC: ActionDefinition(
            action_type=ActionType.PAUSE_TRAFFIC,
            name="Pause Traffic",
            description="Suspends external ingress traffic to stop cascading failure propagation.",
            risk_level=SeverityLevel.CRITICAL,
            required_role=UserRole.ADMIN,
            requires_approval=True,
            parameter_schema=TrafficParameters,
            executor_name="simulated_traffic",
            verification_strategy="traffic_state",
            preconditions=[
                "target_service_exists",
                "privileged_admin_approval",
                "approval_valid",
                "no_conflicting_action",
            ],
            potential_downside="Customers receive 503 Maintenance errors while traffic is paused.",
            expected_outcome="Stops cascading downstream database pool exhaustion.",
        ),
        ActionType.RESUME_TRAFFIC: ActionDefinition(
            action_type=ActionType.RESUME_TRAFFIC,
            name="Resume Traffic",
            description="Restores external ingress routing to target service.",
            risk_level=SeverityLevel.CRITICAL,
            required_role=UserRole.ADMIN,
            requires_approval=True,
            parameter_schema=TrafficParameters,
            executor_name="simulated_traffic",
            verification_strategy="traffic_state",
            preconditions=[
                "target_service_exists",
                "service_is_healthy",
                "privileged_admin_approval",
                "approval_valid",
            ],
            potential_downside="May overwhelm recovered service if warm-up is inadequate.",
            expected_outcome="Standard customer traffic flow is restored.",
        ),
    }

    @classmethod
    def get_definition(cls, action_type: ActionType) -> ActionDefinition:
        """Retrieves registered action definition or raises ValueError."""
        if action_type not in cls._definitions:
            raise ValueError(f"Unknown action type '{action_type}'. Must be one of {[t.value for t in cls._definitions.keys()]}.")
        return cls._definitions[action_type]

    @classmethod
    def validate_parameters(cls, action_type: ActionType, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validates incoming action parameters against the registered Pydantic schema."""
        definition = cls.get_definition(action_type)
        schema_cls = definition.parameter_schema
        validated = schema_cls.model_validate(parameters)
        return validated.model_dump()

    @classmethod
    def list_definitions(cls) -> list[ActionDefinition]:
        """Returns all registered action definitions."""
        return list(cls._definitions.values())
