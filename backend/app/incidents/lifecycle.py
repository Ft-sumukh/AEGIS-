"""Incident lifecycle state machine, transitions, acknowledgement, and resolution manager."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.incidents.audit import IncidentAuditRecorder
from app.incidents.models import InvalidLifecycleTransitionError
from app.models.enums import IncidentStatus
from app.models.incident import Incident

logger = get_logger("aegis.incidents.lifecycle")

# Strict allowed transition mapping
VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.OPEN: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.MITIGATED,
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.INVESTIGATING: {
        IncidentStatus.MITIGATED,
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.MITIGATED: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.CLOSED: set(),  # Terminal state
}


class IncidentLifecycleManager:
    """Enforces strict state transitions, human acknowledgement, and resolution verification."""

    @staticmethod
    def acknowledge(
        db: Session,
        incident: Incident,
        actor: str,
        transition_to_investigating: bool = False,
    ) -> Incident:
        """Records operator acknowledgement of an active incident."""
        now = datetime.now(UTC)
        incident.acknowledged_at = now
        incident.acknowledged_by = actor

        IncidentAuditRecorder.record(
            db=db,
            action="INCIDENT_ACKNOWLEDGED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata={"acknowledged_at": now.isoformat()},
        )

        if transition_to_investigating and incident.status == IncidentStatus.OPEN:
            IncidentLifecycleManager.transition(
                db=db,
                incident=incident,
                new_status=IncidentStatus.INVESTIGATING,
                actor=actor,
                reason="Operator acknowledged and commenced investigation",
            )

        db.flush()
        return incident

    @staticmethod
    def transition(
        db: Session,
        incident: Incident,
        new_status: IncidentStatus,
        actor: str,
        reason: str | None = None,
        resolution_summary: str | None = None,
        closed_by: str | None = None,
    ) -> Incident:
        """Executes a validated lifecycle status transition."""
        curr_status = incident.status

        # If already in the target status, no-op
        if curr_status == new_status:
            return incident

        allowed_targets = VALID_TRANSITIONS.get(curr_status, set())
        if new_status not in allowed_targets:
            raise InvalidLifecycleTransitionError(
                from_status=curr_status,
                to_status=new_status,
                reason=f"Transition from {curr_status.value} to {new_status.value} is not allowed. Terminal states cannot be reopened; valid targets are {[s.value for s in allowed_targets]}.",
            )

        now = datetime.now(UTC)

        # Status-specific validations and timestamp assignments
        if new_status == IncidentStatus.INVESTIGATING:
            if not incident.investigation_started_at:
                incident.investigation_started_at = now

        elif new_status == IncidentStatus.MITIGATED:
            incident.mitigated_at = now

        elif new_status == IncidentStatus.RESOLVED:
            summary = resolution_summary or incident.resolution_summary
            if not summary or not summary.strip():
                raise InvalidLifecycleTransitionError(
                    from_status=curr_status,
                    to_status=new_status,
                    reason="A non-empty resolution summary is required to resolve an incident.",
                )
            incident.resolved_at = now
            incident.resolved_by = actor
            incident.resolution_summary = summary.strip()

        elif new_status == IncidentStatus.CLOSED:
            closer = closed_by or actor
            if not closer or not closer.strip():
                raise InvalidLifecycleTransitionError(
                    from_status=curr_status,
                    to_status=new_status,
                    reason="An authorized closer identifier is required to close an incident.",
                )
            incident.closed_at = now
            incident.closed_by = closer.strip()

        prev_status_val = curr_status.value
        incident.status = new_status

        # Append lifecycle transition to incident metadata
        status_history = list(incident.incident_metadata.get("status_history", []))
        status_history.append(
            {
                "from_status": prev_status_val,
                "to_status": new_status.value,
                "actor": actor,
                "reason": reason,
                "timestamp": now.isoformat(),
            }
        )
        incident.incident_metadata["status_history"] = status_history

        IncidentAuditRecorder.record(
            db=db,
            action="INCIDENT_STATUS_CHANGED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata={
                "previous_status": prev_status_val,
                "new_status": new_status.value,
                "reason": reason,
                "resolution_summary": incident.resolution_summary
                if new_status == IncidentStatus.RESOLVED
                else None,
            },
        )

        db.flush()
        logger.info(
            f"Incident {incident.id} transitioned {prev_status_val} -> {new_status.value} by {actor}"
        )

        try:
            from app.core.events import broadcast_event_sync

            broadcast_event_sync(
                event_type=f"INCIDENT_{new_status.value.upper()}",
                payload={
                    "incident_id": str(incident.id),
                    "title": incident.title,
                    "previous_status": prev_status_val,
                    "new_status": new_status.value,
                    "severity": incident.severity.value,
                    "actor": actor,
                },
                company_id=str(incident.company_id),
            )
        except Exception:
            pass

        return incident
