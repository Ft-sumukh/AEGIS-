"""Centralized AI tool registry enforcing strict allowlisting and arbitrary SQL prevention."""

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.security.audit import SecurityAuditService
from app.security.policy import InvestigationBudgetTracker
from app.security.sanitizer import DataSanitizer

logger = get_logger("aegis.agents.tools.registry")

# Explicitly allowed tools
ALLOWED_TOOLS: set[str] = {
    "get_incident",
    "get_timeline",
    "get_anomalies",
    "get_metric_window",
    "compare_metrics",
    "get_deployments",
    "get_system_events",
    "get_support_tickets",
    "get_customer_complaints",
    "get_impact",
    "get_related_incidents",
    "get_trace",
    "get_trace_summary",
    "get_slow_traces",
    "get_failed_traces",
    "get_service_dependencies",
    "get_service_trace_health",
    "get_critical_path",
    "get_trace_error_patterns",
    "get_correlated_trace_evidence",
}

# Explicitly forbidden tool patterns
FORBIDDEN_TOOLS: set[str] = {
    "execute_sql",
    "execute_query",
    "run_sql",
    "sql_query",
    "execute_python",
    "python_repl",
    "execute_shell",
    "bash",
    "sh",
    "write_database",
    "delete_database",
    "drop_table",
    "read_secret",
    "read_environment",
    "get_env",
    "env",
    "filesystem_access",
    "read_file",
    "write_file",
    "network_request",
    "http_request",
    "curl",
}


class ToolSecurityError(Exception):
    """Raised when an unauthorized or forbidden tool invocation is attempted."""
    pass


class ToolRegistry:
    """Registry maintaining allowlisted operational tools and enforcing security boundaries."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(self, name: str, func: Callable[..., Any], schema: dict[str, Any]) -> None:
        """Registers a tool if it is in the strict allowlist."""
        if name not in ALLOWED_TOOLS:
            raise ToolSecurityError(
                f"Cannot register tool '{name}': not in explicit ALLOWED_TOOLS allowlist."
            )
        self._tools[name] = func
        self._schemas[name] = schema

    def is_allowed(self, name: str) -> bool:
        """Checks whether a tool name is allowlisted."""
        return name in ALLOWED_TOOLS and name not in FORBIDDEN_TOOLS

    def execute(
        self,
        db: Session,
        name: str,
        arguments: dict[str, Any],
        budget_tracker: InvestigationBudgetTracker,
        investigation_id: Any,
        incident_id: Any,
    ) -> dict[str, Any]:
        """Executes an allowlisted tool with data minimization, sanitization, and audit logging."""
        # 1. Reject forbidden or unregistered tools
        if name in FORBIDDEN_TOOLS or not self.is_allowed(name) or name not in self._tools:
            reason = f"Tool '{name}' is forbidden or not allowlisted."
            logger.warning(f"AI Tool Denied: {reason}")
            SecurityAuditService.record_ai_tool_call(
                db=db,
                tool_name=name,
                investigation_id=investigation_id,
                incident_id=incident_id,
                allowed=False,
                record_count=0,
                reason=reason,
            )
            return {
                "status": "DENIED",
                "error": f"Tool '{name}' is forbidden. The AI Investigator cannot execute arbitrary queries or unauthorized tools.",
            }

        # 2. Invoke tool
        tool_fn = self._tools[name]
        try:
            raw_result = tool_fn(db=db, budget_tracker=budget_tracker, **arguments)
            # Count records if list or dict
            record_count = len(raw_result) if isinstance(raw_result, list) else 1
            budget_tracker.record_tool_call(record_count=record_count)

            # 3. Sanitize all tool output data to ensure zero raw secrets or unmasked PII reaches the AI
            sanitized_result = DataSanitizer.sanitize_value(raw_result)

            SecurityAuditService.record_ai_tool_call(
                db=db,
                tool_name=name,
                investigation_id=investigation_id,
                incident_id=incident_id,
                allowed=True,
                record_count=record_count,
            )

            return {
                "status": "SUCCESS",
                "tool": name,
                "data": sanitized_result,
            }
        except Exception as exc:
            logger.exception(f"Error executing AI tool '{name}': {exc}")
            return {
                "status": "ERROR",
                "tool": name,
                "error": str(exc),
            }

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Returns schemas of all registered allowlisted tools."""
        return list(self._schemas.values())
