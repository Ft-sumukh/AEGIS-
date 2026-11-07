"""Unit tests for tool allowlisting, arbitrary SQL prevention, and data minimization."""

import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.orm import Session

from app.agents.tools import get_default_tool_registry
from app.agents.tools.registry import ALLOWED_TOOLS, FORBIDDEN_TOOLS, ToolRegistry
from app.models.company import Company
from app.models.events import Deployment
from app.models.incident import Incident
from app.models.support import CustomerComplaint, SupportTicket
from app.models.enums import (
    CompanyStatus,
    DeploymentStatus,
    IncidentStatus,
    SeverityLevel,
    TicketPriority,
    TicketStatus,
)
from app.security.policy import InvestigationBudgetTracker, TimeWindowExceededError


def test_tool_registry_allowlist_enforcement():
    registry = get_default_tool_registry()

    # All registered tools must be in ALLOWED_TOOLS
    for tool_name in registry._tools:
        assert tool_name in ALLOWED_TOOLS
        assert tool_name not in FORBIDDEN_TOOLS


def test_arbitrary_sql_prevention(db_session: Session):
    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    inv_id = uuid.uuid4()
    inc_id = uuid.uuid4()

    # Attempt forbidden tool: execute_sql
    res = registry.execute(
        db=db_session,
        name="execute_sql",
        arguments={"query": "SELECT * FROM customers;"},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=inc_id,
    )
    assert res["status"] == "DENIED"
    assert "forbidden" in res["error"].lower()


def test_arbitrary_code_and_secret_access_prevention(db_session: Session):
    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    inv_id = uuid.uuid4()
    inc_id = uuid.uuid4()

    for forbidden in ["execute_shell", "execute_python", "read_secret", "delete_database", "filesystem_access"]:
        res = registry.execute(
            db=db_session,
            name=forbidden,
            arguments={"cmd": "whoami"},
            budget_tracker=budget,
            investigation_id=inv_id,
            incident_id=inc_id,
        )
        assert res["status"] == "DENIED"


def test_time_window_limit_enforcement(db_session: Session):
    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    now = datetime.now(UTC)

    # Request window of 72 hours (exceeds 24h default limit)
    start_time = (now - timedelta(hours=72)).isoformat()
    end_time = now.isoformat()

    res = registry.execute(
        db=db_session,
        name="get_metric_window",
        arguments={"metric_name": "checkout_latency", "start_time": start_time, "end_time": end_time},
        budget_tracker=budget,
        investigation_id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
    )
    assert res["status"] == "ERROR"
    assert "exceeds maximum allowed" in res["error"]


def test_data_minimization_support_tickets_and_deployments(db_session: Session):
    now = datetime.now(UTC)

    company = Company(
        name="Test Corp",
        slug=f"test-corp-{uuid.uuid4().hex[:6]}",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()

    # Seed test deployment with secrets in metadata
    dep = Deployment(
        id=uuid.uuid4(),
        company_id=company.id,
        service="payment-service",
        version="v2.1.0",
        environment="production",
        status=DeploymentStatus.SUCCESS,
        deployed_at=now - timedelta(minutes=20),
        deployed_by="ci-deployer",
        deployment_metadata={"git_token": "ghp_secret_repo_token_9988", "db_password": "super_secret_db_pass"},
    )
    db_session.add(dep)

    # Seed test support ticket with customer PII
    ticket = SupportTicket(
        id=uuid.uuid4(),
        company_id=company.id,
        category="PAYMENT",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        summary="Payment failed during checkout. Contact victim.user@example.com or 555-998-1122.",
        created_at=now - timedelta(minutes=15),
    )
    db_session.add(ticket)
    db_session.flush()

    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    inv_id = uuid.uuid4()
    inc_id = uuid.uuid4()

    st = (now - timedelta(hours=1)).isoformat()
    et = (now + timedelta(hours=1)).isoformat()

    # 1. Inspect deployments output
    dep_res = registry.execute(
        db=db_session,
        name="get_deployments",
        arguments={"start_time": st, "end_time": et, "service_name": "payment-service"},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=inc_id,
    )
    assert dep_res["status"] == "SUCCESS"
    dep_data = dep_res["data"]
    assert len(dep_data) >= 1
    for d in dep_data:
        # Verified: metadata stripped, secrets omitted
        assert "metadata" not in d
        assert "deployment_metadata" not in d
        assert "git_token" not in str(d)
        assert "db_password" not in str(d)

    # 2. Inspect support tickets output
    ticket_res = registry.execute(
        db=db_session,
        name="get_support_tickets",
        arguments={"start_time": st, "end_time": et},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=inc_id,
    )
    assert ticket_res["status"] == "SUCCESS"
    ticket_data = ticket_res["data"]
    assert len(ticket_data) >= 1
    found_ticket = next((t for t in ticket_data if "Payment failed" in t.get("summary", "")), None)
    assert found_ticket is not None
    # Verified: PII stripped, ticket pseudonymized
    assert "victim.user@example.com" not in str(found_ticket)
    assert "555-998-1122" not in str(found_ticket)
    assert found_ticket["ticket_reference"].startswith("ticket_")
