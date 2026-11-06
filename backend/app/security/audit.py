"""Security and AI audit logging service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit import AuditLog
from app.models.enums import AuditActorType
from app.security.sanitizer import DataSanitizer

logger = get_logger("aegis.security.audit")


class SecurityAuditEventType:
    """Standardized event types for security, governance, and AI operations."""

    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    INVESTIGATION_COMPLETED = "INVESTIGATION_COMPLETED"
    INVESTIGATION_FAILED = "INVESTIGATION_FAILED"
    AI_TOOL_CALLED = "AI_TOOL_CALLED"
    AI_TOOL_DENIED = "AI_TOOL_DENIED"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_REDACTED = "DATA_REDACTED"
    RECOMMENDATION_CREATED = "RECOMMENDATION_CREATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SECURITY_POLICY_VIOLATION = "SECURITY_POLICY_VIOLATION"


class SecurityAuditService:
    """Persists sanitized, append-only security and AI audit events to AuditLog."""

    @classmethod
    def record_event(
        cls,
        db: Session,
        action: str,
        actor_id: str,
        actor_type: AuditActorType = AuditActorType.USER,
        resource_type: str = "security",
        resource_id: str | None = None,
        company_id: uuid.UUID | None = None,
        request_id: str | None = None,
        result: str = "SUCCESS",
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Persists a sanitized audit entry, strictly scrubbed of any credentials or secrets."""
        # 1. Structure audit payload
        raw_meta = dict(metadata or {})
        raw_meta["result"] = result
        if reason:
            raw_meta["reason"] = reason

        # 2. Sanitize metadata payload recursively to ensure no secrets or PII leak into audit logs
        sanitized_meta = DataSanitizer.sanitize_dict(raw_meta)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            company_id=company_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            timestamp=datetime.now(UTC),
            request_id=request_id,
            audit_metadata=sanitized_meta,
        )

        db.add(audit_entry)
        db.flush()

        logger.info(
            f"Security Audit Event: action={action}, actor={actor_id}, resource={resource_type}:{resource_id}, result={result}"
        )
        return audit_entry

    @classmethod
    def record_ai_investigation_lifecycle(
        cls,
        db: Session,
        action: str,
        investigation_id: uuid.UUID,
        incident_id: uuid.UUID,
        actor_id: str,
        provider: str,
        model: str,
        status: str,
        tool_count: int = 0,
        tools_used: list[str] | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Records diagnostic AI investigation events without persisting hidden reasoning traces."""
        meta = {
            "investigation_id": str(investigation_id),
            "incident_id": str(incident_id),
            "provider": provider,
            "model": model,
            "prompt_version": "v1.0",
            "status": status,
            "tool_count": tool_count,
            "tools_used": tools_used or [],
        }
        return cls.record_event(
            db=db,
            action=action,
            actor_id=actor_id,
            actor_type=AuditActorType.AGENT,
            resource_type="investigation",
            resource_id=str(investigation_id),
            result=status,
            reason=reason,
            metadata=meta,
            request_id=request_id,
        )

    @classmethod
    def record_ai_tool_call(
        cls,
        db: Session,
        tool_name: str,
        investigation_id: uuid.UUID,
        incident_id: uuid.UUID,
        allowed: bool,
        record_count: int = 0,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Records an AI tool invocation or denial."""
        action = (
            SecurityAuditEventType.AI_TOOL_CALLED
            if allowed
            else SecurityAuditEventType.AI_TOOL_DENIED
        )
        meta = {
            "tool_name": tool_name,
            "investigation_id": str(investigation_id),
            "incident_id": str(incident_id),
            "records_returned": record_count,
        }
        return cls.record_event(
            db=db,
            action=action,
            actor_id="aegis_investigator",
            actor_type=AuditActorType.AGENT,
            resource_type="ai_tool",
            resource_id=tool_name,
            result="ALLOWED" if allowed else "DENIED",
            reason=reason,
            metadata=meta,
            request_id=request_id,
        )
