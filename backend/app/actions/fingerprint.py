"""Action parameter fingerprinting and immutability validation."""

import hashlib
import json
from typing import Any


class ActionTamperedError(Exception):
    """Raised when an approved action's parameters or target have been altered before execution."""
    pass


def compute_action_fingerprint(
    action_type: str,
    target_service: str | None,
    parameters: dict[str, Any],
    risk_level: str,
) -> str:
    """Computes a deterministic, canonical SHA-256 fingerprint for an action's execution payload.

    Any subsequent alteration to the action_type, target_service, parameters, or risk_level
    will produce a different hash, enabling the execution engine to detect tampering.
    """
    canonical_payload = {
        "action_type": str(action_type).strip().upper(),
        "target_service": (target_service or "").strip().lower(),
        "parameters": parameters or {},
        "risk_level": str(risk_level).strip().upper(),
    }
    # Sort keys for deterministic canonical JSON representation
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_action_fingerprint(
    action_type: str,
    target_service: str | None,
    parameters: dict[str, Any],
    risk_level: str,
    expected_fingerprint: str | None,
) -> bool:
    """Verifies that the current action parameters match the approved fingerprint."""
    if not expected_fingerprint:
        return False
    current_fingerprint = compute_action_fingerprint(
        action_type=action_type,
        target_service=target_service,
        parameters=parameters,
        risk_level=risk_level,
    )
    return current_fingerprint == expected_fingerprint
