"""Unit tests for Incident Management audit logging and sensitive credential scrubbing."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.incidents.audit import IncidentAuditRecorder
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.enums import AuditActorType, CompanyStatus


def test_audit_recorder_persists_and_sanitizes(db_session: Session) -> None:
    company = Company(
        id=uuid.uuid4(),
        name="Audit Test Co",
        slug=f"audit-{uuid.uuid4().hex[:6]}",
        industry="Security",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident_id = uuid.uuid4()
    metadata = {
        "status": "INVESTIGATING",
        "actor": "operator_admin",
        "password": "super-secret-password",
        "token": "bearer-eyJh...",
        "api_key": "live_key_xyz",
        "safe_field": "12345",
    }

    entry = IncidentAuditRecorder.record(
        db=db_session,
        action="INCIDENT_STATUS_CHANGED",
        incident_id=incident_id,
        company_id=company.id,
        actor_id="admin_user",
        actor_type=AuditActorType.USER,
        metadata=metadata,
        request_id="req-123456",
    )

    assert entry.id is not None
    assert entry.action == "INCIDENT_STATUS_CHANGED"
    assert entry.resource_type == "incident"
    assert entry.resource_id == str(incident_id)

    # Sensitive fields scrubbed
    assert "password" not in entry.audit_metadata
    assert "token" not in entry.audit_metadata
    assert "api_key" not in entry.audit_metadata
    assert entry.audit_metadata["safe_field"] == "12345"

    # Query from DB to verify persistence
    queried = db_session.scalar(select(AuditLog).where(AuditLog.id == entry.id))
    assert queried is not None
    assert queried.actor_id == "admin_user"
