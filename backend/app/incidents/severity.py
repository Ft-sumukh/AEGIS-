"""Deterministic severity determination and monotonic escalation service."""

from app.models.anomaly import Anomaly
from app.models.enums import SeverityLevel

SEVERITY_RANK: dict[SeverityLevel, int] = {
    SeverityLevel.INFO: 0,
    SeverityLevel.LOW: 1,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.WARNING: 3,
    SeverityLevel.HIGH: 4,
    SeverityLevel.ERROR: 5,
    SeverityLevel.CRITICAL: 6,
}


class IncidentSeverityService:
    """Calculates defensible incident severity and manages monotonic severity escalation."""

    @staticmethod
    def calculate_initial_severity(
        anomalies: list[Anomaly],
        affected_metrics: list[str],
        revenue_impact: float = 0.0,
        orders_affected: int = 0,
    ) -> tuple[SeverityLevel, str]:
        """Calculates initial deterministic incident severity with detailed rationale."""
        reasons: list[str] = []
        has_critical_anomaly = any(a.severity == SeverityLevel.CRITICAL for a in anomalies)
        has_high_anomaly = any(
            a.severity in (SeverityLevel.HIGH, SeverityLevel.ERROR) for a in anomalies
        )
        metric_count = len(set(affected_metrics))

        if has_critical_anomaly:
            crit_anoms = [a.metric_name for a in anomalies if a.severity == SeverityLevel.CRITICAL]
            reasons.append(
                f"critical anomaly threshold breached on {', '.join(sorted(set(crit_anoms))[:3])}"
            )

        if revenue_impact >= 2500.0:
            reasons.append(f"estimated revenue impact (${revenue_impact:,.2f}) exceeded threshold")

        if orders_affected >= 50:
            reasons.append(f"estimated order volume impact ({orders_affected} orders) is elevated")

        if metric_count >= 3:
            reasons.append(
                f"{metric_count} dependent operational metrics degraded in temporal cluster"
            )

        # Evaluate final severity tier
        if (
            has_critical_anomaly
            or (has_high_anomaly and metric_count >= 3)
            or revenue_impact >= 10000.0
        ):
            severity = SeverityLevel.CRITICAL
        elif has_high_anomaly or metric_count >= 2 or revenue_impact >= 2500.0:
            severity = SeverityLevel.HIGH
        elif any(a.severity == SeverityLevel.MEDIUM for a in anomalies) or metric_count >= 1:
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.LOW

        if not reasons:
            reasons.append("routine operational anomaly cluster meeting minimum correlation bounds")

        rationale = f"{severity.value} because " + "; ".join(reasons) + "."
        return severity, rationale

    @staticmethod
    def evaluate_escalation(
        current_severity: SeverityLevel,
        proposed_severity: SeverityLevel,
        current_reason: str | None,
        escalation_factor: str,
    ) -> tuple[SeverityLevel, str, bool]:
        """Evaluates whether new evidence justifies a monotonic severity escalation.

        CRITICAL: Severity only escalates upward; it never automatically de-escalates.
        """
        current_rank = SEVERITY_RANK.get(current_severity, 2)
        proposed_rank = SEVERITY_RANK.get(proposed_severity, 2)

        if proposed_rank > current_rank:
            base_reason = current_reason or f"Assigned {current_severity.value}"
            escalated_reason = (
                f"{base_reason} Escalated to {proposed_severity.value} due to: {escalation_factor}."
            )
            return proposed_severity, escalated_reason, True

        return current_severity, current_reason or "", False
