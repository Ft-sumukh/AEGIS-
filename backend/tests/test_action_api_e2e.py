"""End-to-end integration tests for Action & Human Approval REST API endpoints."""

import uuid
from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.actions.infrastructure import SimulatedInfrastructure
from app.models.action import Action
from app.models.company import Company
from app.models.enums import (
    ActionApprovalDecision,
    ActionStatus,
    ActionType,
    CompanyStatus,
    IncidentStatus,
    InvestigationStatus,
    RecommendationStatus,
    SeverityLevel,
    TicketPriority,
    VerificationOutcome,
)
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.metrics import OperationalMetric
from app.models.recommendation import Recommendation


@pytest.fixture
def action_api_fixture(db_session: Session):
    """Seed base scenario for action workflow tests."""
    SimulatedInfrastructure.get_instance().reset()

    company = Company(
        id=uuid.uuid4(),
        name="E2E Action Corp",
        slug=f"e2e-action-{uuid.uuid4().hex[:6]}",
        industry="Technology",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Day 60 Checkout Blackout",
        summary="Payment failure rate elevated to 42.8%",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.OPEN,
        category="APPLICATION",
        affected_systems=["checkout-service"],
        affected_metrics=["error_rate", "checkout_latency"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.flush()

    investigation = Investigation(
        id=uuid.uuid4(),
        incident_id=incident.id,
        summary="Bad deployment identified",
        status=InvestigationStatus.COMPLETED,
    )
    db_session.add(investigation)
    db_session.flush()


    recommendation = Recommendation(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        incident_id=incident.id,
        title="Rollback checkout-service deployment to v4.8.1",
        description="Revert bad deployment release-2026-03-31",
        priority=TicketPriority.HIGH,
        risk_level=SeverityLevel.HIGH,
        expected_impact="Restores checkout success rate",
        status=RecommendationStatus.PROPOSED,
    )
    db_session.add(recommendation)
    db_session.commit()

    return company, incident, recommendation


def test_action_definitions_endpoint(client: TestClient):
    """Verify GET /api/v1/actions/registry/definitions returns catalog."""
    res = client.get("/api/v1/actions/registry/definitions", headers={"X-User-Role": "VIEWER"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 8
    types = [d["action_type"] for d in data]
    assert "ROLLBACK_DEPLOYMENT" in types
    assert "SCALE_SERVICE" in types


def test_full_action_approval_execution_verification_loop(client: TestClient, action_api_fixture, db_session: Session):
    """Verify full lifecycle from Proposal -> Submit -> Approve -> DryRun -> Execute -> Verify."""
    company, incident, recommendation = action_api_fixture

    analyst_headers = {"X-User-Role": "ANALYST", "X-User-Id": "usr-analyst-1", "X-User-Name": "alice_analyst"}
    operator_headers = {"X-User-Role": "OPERATOR", "X-User-Id": "usr-ops-1", "X-User-Name": "bob_operator"}

    # 1. Propose Action
    propose_payload = {
        "recommendation_id": str(recommendation.id),
        "title": "Emergency Rollback to v4.8.1",
        "action_type": "ROLLBACK_DEPLOYMENT",
        "target_service": "checkout-service",
        "parameters": {
            "service": "checkout-service",
            "target_version": "v4.8.1",
        },
    }
    res = client.post(
        f"/api/v1/actions/incidents/{incident.id}",
        json=propose_payload,
        headers=analyst_headers,
    )
    assert res.status_code == 201
    action_data = res.json()
    action_id = action_data["id"]
    assert action_data["status"] == ActionStatus.PROPOSED.value
    assert action_data["fingerprint"] is not None

    # 2. Submit Action for Human Authorization
    res = client.post(
        f"/api/v1/actions/{action_id}/submit",
        json={"notes": "Diagnostics confirm checkout-service deployment is faulty"},
        headers=analyst_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == ActionStatus.PENDING_APPROVAL.value

    # 3. Human Approval (Requires confirmation phrase for HIGH/CRITICAL risk)
    # 3a. Try without confirmation phrase
    res = client.post(
        f"/api/v1/actions/{action_id}/approve",
        json={"decision": "APPROVED", "reason": "Authorized by Incident Lead"},
        headers=operator_headers,
    )
    assert res.status_code == 400
    assert "typed confirmation" in res.json()["detail"].lower()


    # 3b. Approve with valid confirmation phrase
    res = client.post(
        f"/api/v1/actions/{action_id}/approve",
        json={
            "decision": "APPROVED",
            "reason": "Authorized by Incident Lead",
            "confirmation_phrase": "APPROVE ROLLBACK DEPLOYMENT",
        },
        headers=operator_headers,
    )
    assert res.status_code == 200
    approved_action = res.json()
    assert approved_action["status"] == ActionStatus.APPROVED.value
    assert approved_action["approved_by"] == "simulated_operator"
    assert len(approved_action["approvals"]) == 1

    assert approved_action["approvals"][0]["decision"] == ActionApprovalDecision.APPROVED.value

    # 4. Dry Run
    res = client.get(
        f"/api/v1/actions/{action_id}/dry-run",
        headers=operator_headers,
    )
    assert res.status_code == 200
    dry_run_data = res.json()
    assert dry_run_data["dry_run"] is True
    assert dry_run_data["success"] is True

    # 5. Execute Action
    res = client.post(
        f"/api/v1/actions/{action_id}/execute",
        json={"dry_run": False},
        headers=operator_headers,
    )
    assert res.status_code == 200
    exec_data = res.json()
    assert exec_data["success"] is True
    assert exec_data["dry_run"] is False

    # Inject recovered metric into database for verification
    db_session.add(
        OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name="api_error_rate",
            value=0.85,
            unit="percent",
            source="api-gateway",
            timestamp=datetime.now(UTC),
        )
    )
    db_session.commit()

    # 6. Post-execution Verification
    res = client.post(
        f"/api/v1/actions/{action_id}/verify",
        headers=operator_headers,
    )
    assert res.status_code == 200
    verified_data = res.json()
    assert verified_data["outcome"] == VerificationOutcome.VERIFIED_SUCCESS.value
    assert verified_data["signals_verified"] > 0

    # Verify action entity state
    action_res = client.get(f"/api/v1/actions/{action_id}", headers=operator_headers)
    assert action_res.status_code == 200
    assert action_res.json()["status"] == ActionStatus.VERIFIED.value
    assert action_res.json()["verification_status"] == VerificationOutcome.VERIFIED_SUCCESS.value


    # 7. Check Audit Logs contain complete action audit trail
    res = client.get(
        "/api/v1/audit",
        headers={"X-User-Role": "ADMIN"},
    )
    assert res.status_code == 200

    audit_items = res.json()["items"]
    audit_actions = [item["action"] for item in audit_items]
    assert "ACTION_PROPOSED" in audit_actions
    assert "ACTION_APPROVED" in audit_actions
    assert "EXECUTION_COMPLETED" in audit_actions
    assert "VERIFICATION_COMPLETED" in audit_actions



def test_rejection_flow(client: TestClient, action_api_fixture):
    """Verify action rejection transitions to REJECTED and records human justification."""
    _, incident, recommendation = action_api_fixture

    analyst_headers = {"X-User-Role": "ANALYST", "X-User-Id": "usr-analyst-1", "X-User-Name": "alice_analyst"}
    operator_headers = {"X-User-Role": "OPERATOR", "X-User-Id": "usr-ops-1", "X-User-Name": "bob_operator"}

    # Propose
    res = client.post(
        f"/api/v1/actions/incidents/{incident.id}",
        json={
            "recommendation_id": str(recommendation.id),
            "title": "Clear all cache",
            "action_type": "CLEAR_CACHE",
            "target_service": "checkout-service",
            "parameters": {"service": "checkout-service", "cache_tier": "redis_l2"},
        },
        headers=analyst_headers,
    )
    assert res.status_code == 201
    action_id = res.json()["id"]

    # Submit
    client.post(f"/api/v1/actions/{action_id}/submit", json={}, headers=analyst_headers)

    # Reject
    res = client.post(
        f"/api/v1/actions/{action_id}/reject",
        json={"reason": "Flushing cache during high traffic peak will cause cache stampede"},
        headers=operator_headers,
    )
    assert res.status_code == 200
    rejected = res.json()
    assert rejected["status"] == ActionStatus.REJECTED.value
    assert rejected["approval_status"] == "REJECTED"


def test_ai_identity_rejected_at_api(client: TestClient, action_api_fixture, db_session: Session):
    """Verify AI username or agent header cannot call approve or execute."""
    _, incident, recommendation = action_api_fixture

    # Create an action directly
    action = Action(
        id=uuid.uuid4(),
        incident_id=incident.id,
        recommendation_id=recommendation.id,
        title="Rollback action",
        action_type=ActionType.ROLLBACK_DEPLOYMENT,
        target_service="checkout-service",
        parameters={"service": "checkout-service", "target_version": "v4.8.1"},
        risk_level=SeverityLevel.HIGH,
        status=ActionStatus.PENDING_APPROVAL,
        requested_by="alice_analyst",
    )
    db_session.add(action)
    db_session.commit()

    # Try calling approve as AI agent
    ai_headers = {"X-User-Role": "ADMIN", "X-User-Id": "aegis-investigator-01", "X-User-Name": "aegis_ai"}
    res = client.post(
        f"/api/v1/actions/{action.id}/approve",
        json={"decision": "APPROVED", "confirmation_phrase": "APPROVE"},
        headers=ai_headers,
    )
    assert res.status_code == 403
    assert "Autonomous AI agents are strictly forbidden" in res.json()["detail"]
