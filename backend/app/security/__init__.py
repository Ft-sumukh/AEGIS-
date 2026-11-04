"""Security, privacy, and data-governance module for Aegis."""

from app.security.audit import SecurityAuditService, SecurityAuditEventType
from app.security.auth import AuthUser, UserRole, get_current_user, require_role
from app.security.classification import (
    DataClassification,
    get_field_classification,
    is_classification_allowed_for_ai,
)
from app.security.headers import SecurityHeadersMiddleware
from app.security.policy import (
    AIDataPolicyMode,
    DataRetentionPolicy,
    InvestigationBudgetTracker,
    InvestigationLimits,
    ResourceLimitExceededError,
    TimeWindowExceededError,
)
from app.security.pseudonymizer import (
    Pseudonymizer,
    pseudonymize_customer,
    pseudonymize_ticket,
    pseudonymize_user,
)
from app.security.sanitizer import DataSanitizer, SensitiveDataDetector

__all__ = [
    "AIDataPolicyMode",
    "AuthUser",
    "DataClassification",
    "DataRetentionPolicy",
    "DataSanitizer",
    "InvestigationBudgetTracker",
    "InvestigationLimits",
    "Pseudonymizer",
    "ResourceLimitExceededError",
    "SecurityAuditEventType",
    "SecurityAuditService",
    "SecurityHeadersMiddleware",
    "SensitiveDataDetector",
    "TimeWindowExceededError",
    "UserRole",
    "get_current_user",
    "get_field_classification",
    "is_classification_allowed_for_ai",
    "pseudonymize_customer",
    "pseudonymize_ticket",
    "pseudonymize_user",
    "require_role",
]
