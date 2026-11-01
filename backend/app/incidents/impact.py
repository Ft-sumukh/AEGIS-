"""Incident impact calculation, tracking, and delta update service."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.impact import BusinessImpactEngine
from app.analytics.models import BusinessImpactEstimate
from app.incidents.audit import IncidentAuditRecorder
from app.incidents.models import ImpactDelta
from app.incidents.severity import IncidentSeverityService
from app.models.anomaly import Anomaly
from app.models.enums import SeverityLevel
from app.models.incident import Incident


class IncidentImpactService:
    """Calculates and updates business blast radius with explicit 'estimated' semantics."""

    def __init__(self) -> None:
        self.impact_engine = BusinessImpactEngine()

    def estimate_from_anomalies(self, anomalies: list[Anomaly]) -> BusinessImpactEstimate:
        """Calculates preliminary blast radius from an anomaly cluster."""
        return self.impact_engine.estimate_impact(anomalies)

    def update_incident_impact(
        self,
        db: Session,
        incident: Incident,
        new_revenue: float | None = None,
        new_orders: int | None = None,
        new_users: int | None = None,
        new_support: int | None = None,
        actor: str = "system",
    ) -> ImpactDelta:
        """Updates incident impact estimates and records history and delta."""
        prev_rev = float(incident.estimated_revenue_impact or Decimal("0.00"))
        prev_ord = incident.estimated_orders_affected or 0
        prev_usr = incident.estimated_users_affected or 0
        prev_sup = incident.estimated_support_impact or 0

        curr_rev = new_revenue if new_revenue is not None else prev_rev
        curr_ord = new_orders if new_orders is not None else prev_ord
        curr_usr = new_users if new_users is not None else prev_usr
        curr_sup = new_support if new_support is not None else prev_sup

        delta = ImpactDelta(
            current_revenue=round(curr_rev, 2),
            previous_revenue=round(prev_rev, 2),
            revenue_delta=round(curr_rev - prev_rev, 2),
            current_orders=curr_ord,
            previous_orders=prev_ord,
            orders_delta=curr_ord - prev_ord,
            current_users=curr_usr,
            previous_users=prev_usr,
            users_delta=curr_usr - prev_usr,
            current_support=curr_sup,
            previous_support=prev_sup,
            support_delta=curr_sup - prev_sup,
            is_preliminary=True,
        )

        # Update incident entity
        incident.estimated_revenue_impact = Decimal(str(round(curr_rev, 2)))
        incident.estimated_orders_affected = curr_ord
        incident.estimated_users_affected = curr_usr
        incident.estimated_support_impact = curr_sup

        # Persist change in incident metadata history
        history = list(incident.incident_metadata.get("impact_history", []))
        history.append(delta.to_dict())
        incident.incident_metadata["impact_history"] = history
        incident.incident_metadata["last_impact_update_by"] = actor

        # Check for potential severity escalation if blast radius dramatically increased
        if curr_rev >= 10000.0 or curr_ord >= 100:
            escalated_sev, escalated_reason, changed = IncidentSeverityService.evaluate_escalation(
                current_severity=incident.severity,
                proposed_severity=SeverityLevel.CRITICAL,
                current_reason=incident.severity_reason,
                escalation_factor=f"Estimated revenue impact reached ${curr_rev:,.2f} ({curr_ord} orders affected)",
            )
            if changed:
                incident.severity = escalated_sev
                incident.severity_reason = escalated_reason
                IncidentAuditRecorder.record(
                    db=db,
                    action="INCIDENT_SEVERITY_CHANGED",
                    incident_id=incident.id,
                    company_id=incident.company_id,
                    actor_id=actor,
                    metadata={"new_severity": escalated_sev.value, "reason": escalated_reason},
                )

        IncidentAuditRecorder.record(
            db=db,
            action="INCIDENT_IMPACT_UPDATED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata=delta.to_dict(),
        )

        db.flush()
        return delta
