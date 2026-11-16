"""Data classification taxonomy and policy definitions for Aegis operations data."""

from enum import StrEnum
from typing import Any


class DataClassification(StrEnum):
    """Hierarchical data classification levels for operational governance.

    PUBLIC: Safe for unrestricted consumption (generic metadata, public documentation).
    INTERNAL: Standard operational information (service names, deployment versions, aggregate metrics, health stats).
    CONFIDENTIAL: Business-sensitive information (detailed performance, tickets, complaints, system events).
    RESTRICTED: Highly sensitive PII, credentials, tokens, secrets, payment data, passwords.
    """

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# Default field-level classification registry
MODEL_FIELD_CLASSIFICATIONS: dict[str, dict[str, DataClassification]] = {
    "customer": {
        "id": DataClassification.INTERNAL,
        "first_name": DataClassification.RESTRICTED,
        "last_name": DataClassification.RESTRICTED,
        "email": DataClassification.RESTRICTED,
        "phone": DataClassification.RESTRICTED,
        "address": DataClassification.RESTRICTED,
        "company_id": DataClassification.INTERNAL,
        "created_at": DataClassification.INTERNAL,
    },
    "support_ticket": {
        "id": DataClassification.INTERNAL,
        "ticket_id": DataClassification.INTERNAL,
        "requester_email": DataClassification.RESTRICTED,
        "requester_name": DataClassification.RESTRICTED,
        "subject": DataClassification.CONFIDENTIAL,
        "body": DataClassification.CONFIDENTIAL,
        "category": DataClassification.INTERNAL,
        "severity": DataClassification.INTERNAL,
        "status": DataClassification.INTERNAL,
        "created_at": DataClassification.INTERNAL,
    },
    "customer_complaint": {
        "id": DataClassification.INTERNAL,
        "customer_id": DataClassification.RESTRICTED,
        "category": DataClassification.INTERNAL,
        "severity": DataClassification.INTERNAL,
        "details": DataClassification.CONFIDENTIAL,
        "created_at": DataClassification.INTERNAL,
    },
    "system_event": {
        "id": DataClassification.INTERNAL,
        "service_name": DataClassification.INTERNAL,
        "event_type": DataClassification.INTERNAL,
        "severity": DataClassification.INTERNAL,
        "summary": DataClassification.INTERNAL,
        "details": DataClassification.CONFIDENTIAL,
        "timestamp": DataClassification.INTERNAL,
    },
    "deployment": {
        "id": DataClassification.INTERNAL,
        "deployment_id": DataClassification.INTERNAL,
        "service_name": DataClassification.INTERNAL,
        "version": DataClassification.INTERNAL,
        "status": DataClassification.INTERNAL,
        "environment": DataClassification.INTERNAL,
        "started_at": DataClassification.INTERNAL,
        "completed_at": DataClassification.INTERNAL,
        "metadata": DataClassification.CONFIDENTIAL,
    },
    "metric": {
        "id": DataClassification.INTERNAL,
        "metric_name": DataClassification.INTERNAL,
        "service_name": DataClassification.INTERNAL,
        "value": DataClassification.INTERNAL,
        "timestamp": DataClassification.INTERNAL,
        "metric_metadata": DataClassification.INTERNAL,
    },
    "incident": {
        "id": DataClassification.INTERNAL,
        "title": DataClassification.INTERNAL,
        "summary": DataClassification.CONFIDENTIAL,
        "severity": DataClassification.INTERNAL,
        "status": DataClassification.INTERNAL,
        "category": DataClassification.INTERNAL,
        "affected_systems": DataClassification.INTERNAL,
        "affected_metrics": DataClassification.INTERNAL,
        "detected_at": DataClassification.INTERNAL,
    },
    "audit_log": {
        "id": DataClassification.INTERNAL,
        "actor_id": DataClassification.INTERNAL,
        "action": DataClassification.INTERNAL,
        "resource_type": DataClassification.INTERNAL,
        "resource_id": DataClassification.INTERNAL,
        "timestamp": DataClassification.INTERNAL,
        "audit_metadata": DataClassification.CONFIDENTIAL,
    },
}


def get_field_classification(
    model_name: str, field_name: str, default: DataClassification = DataClassification.INTERNAL
) -> DataClassification:
    """Returns the data classification level for a given model attribute."""
    model_map = MODEL_FIELD_CLASSIFICATIONS.get(model_name.lower())
    if model_map:
        return model_map.get(field_name.lower(), default)
    return default


def is_classification_allowed_for_ai(
    classification: DataClassification, policy_mode: str = "STANDARD"
) -> bool:
    """Evaluates whether an entity with the specified classification is permissible for AI ingestion.

    Policy Modes:
    - STRICT: Only PUBLIC and sanitized/minimized INTERNAL data permitted. CONFIDENTIAL & RESTRICTED forbidden.
    - STANDARD: PUBLIC, INTERNAL, and redacted CONFIDENTIAL operational data permitted. RESTRICTED always forbidden.
    - DEVELOPMENT: Synthetic/local data permitted (still blocks unredacted RESTRICTED secrets).
    """
    mode = policy_mode.upper()
    if classification == DataClassification.RESTRICTED:
        return False
    if mode == "STRICT":
        return classification in (DataClassification.PUBLIC, DataClassification.INTERNAL)
    # STANDARD and DEVELOPMENT permit PUBLIC, INTERNAL, and CONFIDENTIAL (once sanitized)
    return True
