"""Unit tests for Action Registry and parameter schemas."""

import pytest
from pydantic import ValidationError

from app.actions.registry import (
    ActionRegistry,
    ClearCacheParameters,
    FeatureFlagParameters,
    RestartServiceParameters,
    RollbackDeploymentParameters,
    ScaleServiceParameters,
    TrafficParameters,
)
from app.models.enums import ActionType, SeverityLevel
from app.security.auth import UserRole


def test_registry_contains_all_action_types():
    """Verify all 8 action types are registered with valid metadata."""
    defs = ActionRegistry.list_definitions()
    assert len(defs) == 8

    action_types = {d.action_type for d in defs}
    expected_types = {
        ActionType.ROLLBACK_DEPLOYMENT,
        ActionType.RESTART_SERVICE,
        ActionType.SCALE_SERVICE,
        ActionType.ENABLE_FEATURE_FLAG,
        ActionType.DISABLE_FEATURE_FLAG,
        ActionType.CLEAR_CACHE,
        ActionType.PAUSE_TRAFFIC,
        ActionType.RESUME_TRAFFIC,
    }
    assert action_types == expected_types


def test_rollback_deployment_parameters_validation():
    """Verify RollbackDeploymentParameters validates valid input and rejects invalid."""
    valid = RollbackDeploymentParameters(
        service="order-service",
        target_version="v2.4.0",
        environment="production",
    )
    assert valid.target_version == "v2.4.0"

    validated_dict = ActionRegistry.validate_parameters(
        ActionType.ROLLBACK_DEPLOYMENT,
        {"service": "order-service", "target_version": "v2.4.0"},
    )
    assert validated_dict["target_version"] == "v2.4.0"

    with pytest.raises(ValidationError):
        ActionRegistry.validate_parameters(
            ActionType.ROLLBACK_DEPLOYMENT,
            {"service": "order-service", "target_version": ""},
        )


def test_scale_service_parameters_validation():
    """Verify ScaleServiceParameters validates replica counts within bounds."""
    valid = ScaleServiceParameters(
        service="payment-service",
        target_capacity=8,
    )
    assert valid.target_capacity == 8

    with pytest.raises(ValidationError):
        ScaleServiceParameters(service="payment-service", target_capacity=0)

    with pytest.raises(ValidationError):
        ScaleServiceParameters(service="payment-service", target_capacity=100)


def test_traffic_parameters_validation():
    """Verify TrafficParameters validates traffic percentages and actions."""
    valid = TrafficParameters(service="checkout-service", action="PAUSE", traffic_percentage=0)
    assert valid.traffic_percentage == 0

    with pytest.raises(ValidationError):
        TrafficParameters(service="checkout-service", action="PAUSE", traffic_percentage=-5)

    with pytest.raises(ValidationError):
        TrafficParameters(service="checkout-service", action="INVALID_ACTION", traffic_percentage=50)


def test_feature_flag_parameters_validation():
    """Verify FeatureFlagParameters validates flag keys."""
    valid = FeatureFlagParameters(flag_name="checkout_v2_new_gateway", enabled=True)
    assert valid.flag_name == "checkout_v2_new_gateway"

    with pytest.raises(ValidationError):
        FeatureFlagParameters(flag_name="")


def test_clear_cache_parameters_validation():
    """Verify ClearCacheParameters defaults and validation."""
    valid = ClearCacheParameters(service="order-service")
    assert valid.service == "order-service"
    assert valid.cache_tier == "redis_l2"

