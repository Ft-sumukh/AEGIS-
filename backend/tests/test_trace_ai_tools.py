"""Unit tests for AI Investigator trace investigation tools, allowlisting, and safety bounds."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.agents.tools import get_default_tool_registry
from app.agents.tools.registry import ALLOWED_TOOLS
from app.models.company import Company
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.trace import TraceSpan
from app.security.policy import InvestigationBudgetTracker


def test_trace_tools_registered_in_allowlist() -> None:
    """Verify all Phase 2 trace investigation tools are registered and allowlisted."""
    registry = get_default_tool_registry()
    trace_tool_names = [
        "get_trace",
        "get_trace_summary",
        "get_slow_traces",
        "get_failed_traces",
        "get_service_dependencies",
        "get_service_trace_health",
        "get_critical_path",
        "get_trace_error_patterns",
        "get_correlated_trace_evidence",
    ]
    for tool_name in trace_tool_names:
        assert tool_name in ALLOWED_TOOLS
        assert tool_name in registry._tools


def test_ai_tool_get_trace_and_critical_path(db_session: Session) -> None:
    """Verify safe invocation of get_trace and get_critical_path by AI Investigator."""
    company = Company(
        id=uuid.uuid4(),
        name="AI Tool Corp",
        slug=f"aitool-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    now = datetime.now(UTC)
    trace_id = "ai-trace-tool-01"

    # Create root and child spans
    root = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="ai-root",
        parent_span_id=None,
        timestamp_start=now,
        timestamp_end=now + timedelta(milliseconds=450),
        duration_ms=450.0,
        service_name="api-gateway",
        operation_name="GET /status",
        status="OK",
    )
    child = TraceSpan(
        id=uuid.uuid4(),
        company_id=company.id,
        trace_id=trace_id,
        span_id="ai-child",
        parent_span_id="ai-root",
        timestamp_start=now + timedelta(milliseconds=10),
        timestamp_end=now + timedelta(milliseconds=400),
        duration_ms=390.0,
        service_name="status-service",
        operation_name="check",
        status="OK",
    )
    db_session.add_all([root, child])
    db_session.commit()

    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    inv_id = uuid.uuid4()
    inc_id = uuid.uuid4()

    # 1. Execute get_trace tool
    res_trace = registry.execute(
        db=db_session,
        name="get_trace",
        arguments={"trace_id": trace_id},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=inc_id,
    )
    assert res_trace["status"] == "SUCCESS"
    assert res_trace["data"]["trace_id"] == trace_id
    assert res_trace["data"]["spans_count"] == 2

    # 2. Execute get_critical_path tool
    res_cp = registry.execute(
        db=db_session,
        name="get_critical_path",
        arguments={"trace_id": trace_id},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=inc_id,
    )
    assert res_cp["status"] == "SUCCESS"
    assert res_cp["data"]["trace_id"] == trace_id
    assert len(res_cp["data"]["segments"]) >= 1


def test_ai_tool_get_correlated_trace_evidence(db_session: Session) -> None:
    """Verify safe invocation of get_correlated_trace_evidence tool for an incident."""
    company = Company(
        id=uuid.uuid4(),
        name="Corr Tool Corp",
        slug=f"corrtool-{uuid.uuid4().hex[:6]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(company)
    db_session.commit()

    incident = Incident(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Payment Error Surge",
        summary="Spike in 504 gateway timeout responses",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.INVESTIGATING,
        category="PAYMENTS",
        affected_systems=["payment-gateway"],
        detected_at=datetime.now(UTC),
    )
    db_session.add(incident)
    db_session.commit()

    registry = get_default_tool_registry()
    budget = InvestigationBudgetTracker()
    inv_id = uuid.uuid4()

    res = registry.execute(
        db=db_session,
        name="get_correlated_trace_evidence",
        arguments={"incident_id": str(incident.id)},
        budget_tracker=budget,
        investigation_id=inv_id,
        incident_id=incident.id,
    )
    assert res["status"] == "SUCCESS"
    assert res["data"]["incident_id"] == str(incident.id)
    assert "non_causal_synthesis" in res["data"]
