"""Unit tests for security and AI audit logging."""

import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditActorType
from app.security.audit import SecurityAuditService, SecurityAuditEventType


def test_security_audit_event_recording(db_session: Session):
    user_id = "usr-audit-test"
    entry = SecurityAuditService.record_event(
        db=db_session,
        action=SecurityAuditEventType.LOGIN,
        actor_id=user_id,
        resource_type="session",
        resource_id="sess-1234",
        result="SUCCESS",
        metadata={"ip": "10.0.0.1", "auth_method": "bearer_token"},
    )
    db_session.commit()

    saved = db_session.get(AuditLog, entry.id)
    assert saved is not None
    assert saved.action == SecurityAuditEventType.LOGIN
    assert saved.actor_id == user_id
    assert saved.audit_metadata["result"] == "SUCCESS"


def test_audit_metadata_secrets_scrubbed(db_session: Session):
    # Metadata intentionally contains sensitive password and API key
    meta = {
        "user_email": "admin@aegis.internal",
        "api_key": "sk-secret-ai-token-12345",
        "password": "SuperSecretPassword!",
        "database_url": "postgresql://usr:secret_pass@localhost:5432/db",
    }
    entry = SecurityAuditService.record_event(
        db=db_session,
        action=SecurityAuditEventType.SECURITY_POLICY_VIOLATION,
        actor_id="bad_actor",
        metadata=meta,
    )
    db_session.commit()

    saved = db_session.get(AuditLog, entry.id)
    assert saved is not None
    # Verify sensitive keys were scrubbed/masked
    assert saved.audit_metadata["api_key"] == "[REDACTED]"
    assert saved.audit_metadata["password"] == "[REDACTED]"
    assert "admin@aegis.internal" not in str(saved.audit_metadata)
    assert "secret_pass" not in str(saved.audit_metadata)


def test_ai_tool_audit_trail(db_session: Session):
    inv_id = uuid.uuid4()
    inc_id = uuid.uuid4()

    # Record allowed tool call
    allowed_entry = SecurityAuditService.record_ai_tool_call(
        db=db_session,
        tool_name="get_incident",
        investigation_id=inv_id,
        incident_id=inc_id,
        allowed=True,
        record_count=1,
    )

    # Record denied tool call
    denied_entry = SecurityAuditService.record_ai_tool_call(
        db=db_session,
        tool_name="execute_sql",
        investigation_id=inv_id,
        incident_id=inc_id,
        allowed=False,
        record_count=0,
        reason="Forbidden tool",
    )
    db_session.commit()

    assert allowed_entry.action == SecurityAuditEventType.AI_TOOL_CALLED
    assert allowed_entry.audit_metadata["result"] == "ALLOWED"

    assert denied_entry.action == SecurityAuditEventType.AI_TOOL_DENIED
    assert denied_entry.audit_metadata["result"] == "DENIED"
    assert denied_entry.audit_metadata["reason"] == "Forbidden tool"
