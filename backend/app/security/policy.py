"""Privacy policy, resource limits, and data retention configurations."""

import time
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import NamedTuple

from app.config import get_settings


class AIDataPolicyMode(StrEnum):
    """Data governance modes for AI operational context ingestion."""

    STRICT = "STRICT"
    STANDARD = "STANDARD"
    DEVELOPMENT = "DEVELOPMENT"


class InvestigationLimits(NamedTuple):
    """Immutable bounds on AI investigation queries and execution."""

    max_query_window_hours: int
    max_records_per_tool_call: int
    max_context_records: int
    max_tool_calls: int
    max_duration_seconds: int

    @classmethod
    def from_settings(cls) -> "InvestigationLimits":
        settings = get_settings()
        return cls(
            max_query_window_hours=settings.MAX_QUERY_WINDOW_HOURS,
            max_records_per_tool_call=settings.MAX_RECORDS_PER_TOOL_CALL,
            max_context_records=settings.MAX_CONTEXT_RECORDS,
            max_tool_calls=settings.MAX_TOOL_CALLS_PER_INVESTIGATION,
            max_duration_seconds=settings.MAX_INVESTIGATION_DURATION_SECONDS,
        )


class InvestigationBudgetTracker:
    """Tracks and enforces tool calls and execution limits for an active AI investigation run."""

    def __init__(self, limits: InvestigationLimits | None = None) -> None:
        self.limits = limits or InvestigationLimits.from_settings()
        self.start_time = time.perf_counter()
        self.tool_call_count = 0
        self.total_records_retrieved = 0
        self.is_constrained = False
        self.constraint_reason: str | None = None

    def record_tool_call(self, record_count: int = 0) -> None:
        """Records consumption of a tool call and validates budget limits."""
        self.tool_call_count += 1
        self.total_records_retrieved += record_count

        elapsed = time.perf_counter() - self.start_time
        if self.tool_call_count > self.limits.max_tool_calls:
            self.is_constrained = True
            self.constraint_reason = (
                f"Maximum tool call limit ({self.limits.max_tool_calls}) reached."
            )
            raise ResourceLimitExceededError(self.constraint_reason)

        if elapsed > self.limits.max_duration_seconds:
            self.is_constrained = True
            self.constraint_reason = (
                f"Investigation duration exceeded deadline ({self.limits.max_duration_seconds}s)."
            )
            raise ResourceLimitExceededError(self.constraint_reason)

        if self.total_records_retrieved > self.limits.max_context_records:
            self.is_constrained = True
            self.constraint_reason = (
                f"Total context evidence records limit ({self.limits.max_context_records}) exceeded."
            )
            raise ResourceLimitExceededError(self.constraint_reason)

    def validate_time_window(self, start_time: datetime, end_time: datetime) -> None:
        """Validates that requested query window does not exceed max allowed hours."""
        delta = end_time - start_time
        max_delta = timedelta(hours=self.limits.max_query_window_hours)
        if delta > max_delta:
            raise TimeWindowExceededError(
                f"Requested query window of {delta} exceeds maximum allowed {max_delta}."
            )


class ResourceLimitExceededError(Exception):
    """Raised when an investigation exceeds configured budget limits."""
    pass


class TimeWindowExceededError(Exception):
    """Raised when an investigation tool requests an excessively wide time window."""
    pass


class DataRetentionPolicy:
    """Configurable data retention schedules."""

    @staticmethod
    def get_retention_days() -> dict[str, int]:
        settings = get_settings()
        return {
            "audit_log": settings.AUDIT_LOG_RETENTION_DAYS,
            "investigation": settings.INVESTIGATION_RETENTION_DAYS,
            "operational_event": settings.OPERATIONAL_EVENT_RETENTION_DAYS,
            "analytics": settings.ANALYTICS_RETENTION_DAYS,
        }
