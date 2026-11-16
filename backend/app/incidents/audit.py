"""Audit logging utility for Incident Management subsystem operations."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit import AuditLog
from app.models.enums import AuditActorType

logger = get_logger("aegis.incidents.audit")


class IncidentAuditRecorder:
    """Records immutable, sanitized audit entries for all incident operations."""

    @staticmethod
    def record(
        db: Session,
        action: str,
        incident_id: uuid.UUID,
        company_id: uuid.UUID | None,
        actor_id: str,
        actor_type: AuditActorType = AuditActorType.USER,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Persists a sanitized append-only audit event."""
        sanitized_meta = dict(metadata or {})
        # Scrub any potential credentials or sensitive tokens from metadata
        for sensitive_key in ("password", "token", "secret", "authorization", "api_key"):
            sanitized_meta.pop(sensitive_key, None)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            company_id=company_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type="incident",
            resource_id=str(incident_id),
            timestamp=datetime.now(UTC),
            request_id=request_id,
            audit_metadata=sanitized_meta,
        )

        db.add(audit_entry)
        # Flush to register in the active transaction
        db.flush()

        logger.info(
            f"Audit event recorded: action={action}, incident_id={incident_id}, actor={actor_id}"
        )
        return audit_entry
