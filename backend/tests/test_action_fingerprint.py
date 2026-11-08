"""Unit tests for Action parameter fingerprinting and tamper detection."""

import pytest

from app.actions.fingerprint import (
    ActionTamperedError,
    compute_action_fingerprint,
    verify_action_fingerprint,
)
from app.models.enums import ActionType, SeverityLevel


def test_fingerprint_deterministic_and_order_independent():
    """Verify compute_action_fingerprint yields same hash regardless of key order."""
    fp1 = compute_action_fingerprint(
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="order-service",
        parameters={"target_version": "v1.0.0", "target_commit": "abc1234"},
        risk_level=SeverityLevel.HIGH,
    )

    # Inverted parameter order
    fp2 = compute_action_fingerprint(
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="order-service",
        parameters={"target_commit": "abc1234", "target_version": "v1.0.0"},
        risk_level=SeverityLevel.HIGH,
    )

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex digest length


def test_fingerprint_detects_parameter_tampering():
    """Verify tampering with parameters changes the fingerprint and fails verification."""
    original_fp = compute_action_fingerprint(
        action_type=ActionType.SCALE_SERVICE,
        target_service="payment-service",
        parameters={"target_replicas": 5},
        risk_level=SeverityLevel.MEDIUM,
    )

    # Valid check
    assert verify_action_fingerprint(
        action_type=ActionType.SCALE_SERVICE,
        target_service="payment-service",
        parameters={"target_replicas": 5},
        risk_level=SeverityLevel.MEDIUM,
        expected_fingerprint=original_fp,
    ) is True

    # Tampered parameter value
    assert verify_action_fingerprint(
        action_type=ActionType.SCALE_SERVICE,
        target_service="payment-service",
        parameters={"target_replicas": 50},  # Tampered
        risk_level=SeverityLevel.MEDIUM,
        expected_fingerprint=original_fp,
    ) is False


def test_fingerprint_detects_service_or_risk_tampering():
    """Verify tampering with target service or risk level fails verification."""
    original_fp = compute_action_fingerprint(
        action_type=ActionType.RESTART_SERVICE,
        target_service="auth-service",
        parameters={"graceful": True},
        risk_level=SeverityLevel.MEDIUM,
    )

    # Tampered service
    assert verify_action_fingerprint(
        action_type=ActionType.RESTART_SERVICE,
        target_service="core-database",  # Tampered service
        parameters={"graceful": True},
        risk_level=SeverityLevel.MEDIUM,
        expected_fingerprint=original_fp,
    ) is False

    # Tampered risk level
    assert verify_action_fingerprint(
        action_type=ActionType.RESTART_SERVICE,
        target_service="auth-service",
        parameters={"graceful": True},
        risk_level=SeverityLevel.LOW,  # Tampered risk
        expected_fingerprint=original_fp,
    ) is False

