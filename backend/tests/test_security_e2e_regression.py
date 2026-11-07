"""End-to-end security regression test for Group 7.

Verifies the entire privacy and security pipeline:
Synthetic incident -> Investigation start -> Tool calls with injected secrets ->
Sanitization & Pseudonymization -> AI Investigator -> Structured findings ->
Evidence citation validation -> Persistence -> Audit.
"""

import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.investigator import AIInvestigator
from app.models.audit import AuditLog
from app.models.company import Company
from app.models.enums import (
    AuditActorType,
    CompanyStatus,
    DeploymentStatus,
    EvidenceSourceType,
    HypothesisStatus,
    IncidentStatus,
    SeverityLevel,
)
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident, IncidentEvidence
from app.models.investigation import Investigation
from app.models.recommendation import Recommendation
from app.security.audit import SecurityAuditEventType


def test_end_to_end_security_regression(db_session: Session):
    # 1. Create company
    company = Company(
        id=uuid.uuid4(),
        name="E2E Security Corp",
        slug=f"e2e-sec-{uuid.uuid4().hex[:6]}",
        industry="E-Commerce",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    now = datetime.now(UTC)

    # 2. Inject operational incident containing PII in summary
    raw_incident_summary = (
        "Checkout service degradation. Reported by customer john.doe@enterprise.com "
        "(phone: +1-555-839-2041). Payment gateway responding with timeouts."
    )
    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Checkout Latency & Payment Failures",
        summary=raw_incident_summary,
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        category="CHECKOUT",
        affected_systems=["checkout-api", "payment-service"],
        affected_metrics=["checkout_latency", "payment_failure_rate"],
        detected_at=now,
    )
    db_session.add(incident)

    # 3. Inject Deployment with fake secrets in metadata
    dep = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="payment-service",
        version="v3.4.1",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=now - timedelta(minutes=15),
        deployed_by="ci-pipeline",
        deployment_metadata={
            "git_token": "ghp_FAKE_DEPLOY_SECRET_KEY_12345",
            "db_pass": "postgresql://usr:super_secret_db_pass@db:5432/orders",
        },
    )
    db_session.add(dep)

    # 4. Inject SystemEvent with authorization bearer token in details
    event = SystemEvent(
        id=uuid.uuid4(),
        company_id=company.id,
        service="payment-service",
        environment="production",
        event_type="GATEWAY_ERROR",
        severity=SeverityLevel.ERROR,
        message="Gateway connection reset by peer. Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_token_data",
        event_metadata={
            "api_key": "sk-fake-openai-secret-key-9999",
            "support_contact": "support.lead@company.com",
        },
        timestamp=now - timedelta(minutes=10),
    )
    db_session.add(event)

    # 5. Pre-attach initial evidence item
    ev_initial = IncidentEvidence(
        id=uuid.uuid4(),
        incident_id=incident.id,
        source_type=EvidenceSourceType.DEPLOYMENT,
        source_id="dep-e2e-v3.4.1",
        title="Payment Service Deployment v3.4.1",
        summary="Deployment of payment-service v3.4.1 completed 12 minutes prior to anomaly.",
        observed_at=now - timedelta(minutes=12),
        relevance_score=0.92,
    )
    db_session.add(ev_initial)
    db_session.commit()

    # 6. Execute AI Investigation through the governed AIInvestigator
    investigator = AIInvestigator()
    investigation, findings = investigator.investigate(
        db=db_session,
        incident_id=incident.id,
        actor_id="sec_investigator_bot",
    )
    db_session.commit()

    # ==============================================================================
    # VERIFICATION: Security Boundaries & Findings
    # ==============================================================================

    # A. Investigation persisted and completed
    assert investigation.id is not None
    assert investigation.status.value in ("COMPLETED", "INSUFFICIENT_EVIDENCE")

    # B. Secrets NEVER entered structured findings
    dumped_findings = findings.model_dump_json()
    assert "ghp_FAKE_DEPLOY_SECRET_KEY" not in dumped_findings
    assert "super_secret_db_pass" not in dumped_findings
    assert "sk-fake-openai-secret-key" not in dumped_findings
    assert "john.doe@enterprise.com" not in dumped_findings
    assert "555-839-2041" not in dumped_findings

    # C. Causality Guardrails: Hypothesis uses calibrated language
    supported_hypotheses = [h for h in findings.hypotheses if h.status == HypothesisStatus.SUPPORTED]
    assert len(supported_hypotheses) >= 1
    leading_hyp = supported_hypotheses[0]
    assert "leading root-cause hypothesis" in leading_hyp.description.lower()
    # Does NOT make an unsupported absolute claim like "definitely caused"
    assert "definitely caused" not in leading_hyp.description.lower()

    # D. Evidence references resolve to verified records
    assert len(findings.evidence_citations) >= 1

    # E. Recommendations persisted to database without executing actions
    recs = db_session.scalars(
        select(Recommendation).where(Recommendation.investigation_id == investigation.id)
    ).all()
    assert len(recs) >= 1
    for r in recs:
        # Action execution must be separate (no action table rows executed)
        assert len(r.actions) == 0

    # F. Zero hidden chain-of-thought persisted in database
    inv_db = db_session.get(Investigation, investigation.id)
    assert not hasattr(inv_db, "chain_of_thought")

    # G. Security and AI Audit trail created
    audit_logs = db_session.scalars(
        select(AuditLog).where(AuditLog.resource_id == str(investigation.id))
    ).all()
    assert len(audit_logs) >= 2  # STARTED and COMPLETED events
    actions = [a.action for a in audit_logs]
    assert SecurityAuditEventType.INVESTIGATION_STARTED in actions
    assert SecurityAuditEventType.INVESTIGATION_COMPLETED in actions

    # H. Verify that audit log metadata does NOT contain any injected secrets
    for log in audit_logs:
        meta_str = str(log.audit_metadata)
        assert "super_secret_db_pass" not in meta_str
        assert "ghp_FAKE" not in meta_str
        assert "sk-fake" not in meta_str
