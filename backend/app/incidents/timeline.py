"""Chronological multi-source timeline engine with deterministic non-causal descriptions and privacy masking."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.incidents.models import TimelineEvent
from app.models.enums import EvidenceSourceType, IncidentStatus
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident
from app.models.support import CustomerComplaint, SupportTicket
from app.models.trace import TraceSpan

# Privacy scrubbers
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def mask_pii(text: str) -> str:
    """Deterministic privacy scrubber removing emails and phone numbers from user feedback."""
    if not text:
        return ""
    scrubbed = EMAIL_PATTERN.sub("[REDACTED EMAIL]", text)
    scrubbed = PHONE_PATTERN.sub("[REDACTED PHONE]", scrubbed)
    return scrubbed


class IncidentTimelineService:
    """Aggregates and formats an incident's chronological timeline across heterogeneous operational sources."""

    @classmethod
    def build_timeline(
        cls,
        db: Session,
        incident: Incident,
        ascending: bool = True,
        include_adjacent_events: bool = True,
    ) -> list[TimelineEvent]:
        """Builds a unified chronological timeline for an incident."""
        events: list[TimelineEvent] = []
        seen_source_keys: set[str] = set()

        # 1. Incident Creation Milestone
        events.append(
            TimelineEvent(
                event_id=f"lifecycle-create-{incident.id}",
                event_type="INCIDENT_CREATED",
                timestamp=incident.detected_at,
                title="Operational incident opened",
                summary=f"Incident identified with initial severity {incident.severity.value}. Affected metrics: {', '.join(incident.affected_metrics)}.",
                severity=incident.severity,
                metadata={
                    "status": IncidentStatus.OPEN.value,
                    "affected_metrics": incident.affected_metrics,
                    "category": incident.category,
                },
            )
        )

        # 2. Lifecycle Milestones & Status History
        if incident.acknowledged_at:
            events.append(
                TimelineEvent(
                    event_id=f"lifecycle-ack-{incident.id}",
                    event_type="INCIDENT_ACKNOWLEDGED",
                    timestamp=incident.acknowledged_at,
                    title="Incident acknowledged",
                    summary=f"Incident acknowledged by operator '{incident.acknowledged_by or 'Unknown'}'.",
                    metadata={"acknowledged_by": incident.acknowledged_by},
                )
            )

        status_history = incident.incident_metadata.get("status_history", [])
        for idx, transition in enumerate(status_history):
            t_time = datetime.fromisoformat(transition["timestamp"])
            events.append(
                TimelineEvent(
                    event_id=f"lifecycle-trans-{incident.id}-{idx}",
                    event_type="STATUS_CHANGED",
                    timestamp=t_time,
                    title=f"Status changed to {transition['to_status']}",
                    summary=f"Transitioned from {transition['from_status']} to {transition['to_status']} by {transition['actor']}. Reason: {transition.get('reason') or 'No reason specified'}.",
                    metadata=transition,
                )
            )

        # 3. Attached Evidence Items
        evidence_items = list(incident.evidence)
        for ev in evidence_items:
            key = f"{ev.source_type.value}:{ev.source_id}" if ev.source_id else str(ev.id)
            seen_source_keys.add(key)
            events.append(
                TimelineEvent(
                    event_id=f"evidence-{ev.id}",
                    event_type="EVIDENCE_ADDED",
                    timestamp=ev.observed_at,
                    title=ev.title,
                    summary=mask_pii(ev.summary),
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    metadata={
                        "relevance_score": ev.relevance_score,
                        "evidence_metadata": ev.evidence_metadata,
                    },
                )
            )

        # 4. Attached Notes
        for note in incident.notes:
            events.append(
                TimelineEvent(
                    event_id=f"note-{note.id}",
                    event_type="NOTE_ADDED",
                    timestamp=note.created_at,
                    title=f"Operator note by {note.author}",
                    summary=mask_pii(note.text),
                    metadata={"author": note.author},
                )
            )

        # 5. Direct Associated Anomalies
        for anom in incident.anomalies:
            key = f"{EvidenceSourceType.ANOMALY.value}:{anom.id}"
            if key not in seen_source_keys:
                seen_source_keys.add(key)
                events.append(
                    TimelineEvent(
                        event_id=f"anomaly-{anom.id}",
                        event_type="ANOMALY_DETECTED",
                        timestamp=anom.detected_at,
                        title=f"Metric anomaly on {anom.metric_name}",
                        summary=(
                            f"Observed value {anom.observed_value} deviated from expected {anom.expected_value} "
                            f"(deviation: {anom.deviation:.2f}σ)."
                        ),
                        severity=anom.severity,
                        source_type=EvidenceSourceType.ANOMALY,
                        source_id=str(anom.id),
                        metadata={
                            "metric_name": anom.metric_name,
                            "observed_value": anom.observed_value,
                            "expected_value": anom.expected_value,
                        },
                    )
                )

        # 6. Temporal Window Adjacent Events (if requested)
        if include_adjacent_events:
            window_start = incident.detected_at - timedelta(hours=2)
            window_end = (incident.resolved_at or datetime.now(UTC)) + timedelta(hours=1)

            # Adjacent Deployments
            dep_stmt = (
                select(Deployment)
                .where(
                    Deployment.company_id == incident.company_id,
                    Deployment.deployed_at >= window_start,
                    Deployment.deployed_at <= window_end,
                )
                .order_by(Deployment.deployed_at.asc())
            )
            deployments = db.scalars(dep_stmt).all()
            for dep in deployments:
                key = f"{EvidenceSourceType.DEPLOYMENT.value}:{dep.id}"
                if key not in seen_source_keys:
                    seen_source_keys.add(key)
                    timing_desc = (
                        "shortly before observed metric degradation"
                        if dep.deployed_at <= incident.detected_at
                        else "during incident window"
                    )
                    events.append(
                        TimelineEvent(
                            event_id=f"deployment-{dep.id}",
                            event_type="DEPLOYMENT",
                            timestamp=dep.deployed_at,
                            title=f"Deployment of {dep.service} ({dep.version})",
                            summary=(
                                f"Service {dep.service} version {dep.version} was deployed to {dep.environment} "
                                f"by {dep.deployed_by} ({timing_desc})."
                            ),
                            source_type=EvidenceSourceType.DEPLOYMENT,
                            source_id=str(dep.id),
                            metadata={
                                "service": dep.service,
                                "version": dep.version,
                                "environment": dep.environment,
                                "status": dep.status.value,
                            },
                        )
                    )

            # Adjacent System Events
            ev_stmt = (
                select(SystemEvent)
                .where(
                    SystemEvent.company_id == incident.company_id,
                    SystemEvent.timestamp >= window_start,
                    SystemEvent.timestamp <= window_end,
                )
                .order_by(SystemEvent.timestamp.asc())
            )
            sys_events = db.scalars(ev_stmt).all()
            for syse in sys_events:
                key = f"{EvidenceSourceType.SYSTEM_EVENT.value}:{syse.id}"
                if key not in seen_source_keys:
                    seen_source_keys.add(key)
                    events.append(
                        TimelineEvent(
                            event_id=f"system-event-{syse.id}",
                            event_type="SYSTEM_EVENT",
                            timestamp=syse.timestamp,
                            title=f"System event: {syse.event_type} on {syse.service}",
                            summary=f"{syse.message} (Severity: {syse.severity.value})",
                            severity=syse.severity,
                            source_type=EvidenceSourceType.SYSTEM_EVENT,
                            source_id=str(syse.id),
                            metadata={"service": syse.service, "event_type": syse.event_type},
                        )
                    )

            # Adjacent Support Tickets (Masked PII)
            ticket_stmt = (
                select(SupportTicket)
                .where(
                    SupportTicket.company_id == incident.company_id,
                    SupportTicket.created_at >= window_start,
                    SupportTicket.created_at <= window_end,
                )
                .order_by(SupportTicket.created_at.asc())
            )
            tickets = db.scalars(ticket_stmt).all()
            for tkt in tickets:
                key = f"{EvidenceSourceType.SUPPORT_TICKET.value}:{tkt.id}"
                if key not in seen_source_keys:
                    seen_source_keys.add(key)
                    events.append(
                        TimelineEvent(
                            event_id=f"support-ticket-{tkt.id}",
                            event_type="SUPPORT_TICKET",
                            timestamp=tkt.created_at,
                            title=f"Support ticket: {tkt.category} ({tkt.priority.value})",
                            summary=mask_pii(tkt.summary),
                            source_type=EvidenceSourceType.SUPPORT_TICKET,
                            source_id=str(tkt.id),
                            metadata={
                                "category": tkt.category,
                                "priority": tkt.priority.value,
                                "status": tkt.status.value,
                            },
                        )
                    )

            # Adjacent Customer Complaints (Masked PII)
            complaint_stmt = (
                select(CustomerComplaint)
                .where(
                    CustomerComplaint.company_id == incident.company_id,
                    CustomerComplaint.created_at >= window_start,
                    CustomerComplaint.created_at <= window_end,
                )
                .order_by(CustomerComplaint.created_at.asc())
            )
            complaints = db.scalars(complaint_stmt).all()
            for cmp in complaints:
                key = f"{EvidenceSourceType.CUSTOMER_COMPLAINT.value}:{cmp.id}"
                if key not in seen_source_keys:
                    seen_source_keys.add(key)
                    events.append(
                        TimelineEvent(
                            event_id=f"customer-complaint-{cmp.id}",
                            event_type="CUSTOMER_COMPLAINT",
                            timestamp=cmp.created_at,
                            title=f"Customer complaint: {cmp.category}",
                            summary=mask_pii(cmp.summary),
                            severity=cmp.severity,
                            source_type=EvidenceSourceType.CUSTOMER_COMPLAINT,
                            source_id=str(cmp.id),
                            metadata={"category": cmp.category},
                        )
                    )

            # Adjacent Trace Spans (Latency spikes & errors)
            trace_stmt = (
                select(TraceSpan)
                .where(
                    TraceSpan.company_id == incident.company_id,
                    TraceSpan.timestamp_start >= window_start,
                    TraceSpan.timestamp_start <= window_end,
                    (TraceSpan.status == "ERROR") | (TraceSpan.duration_ms >= 1000.0),
                )
                .order_by(TraceSpan.timestamp_start.asc())
                .limit(10)
            )
            adjacent_spans = db.scalars(trace_stmt).all()
            for sp in adjacent_spans:
                key = f"TRACE:{sp.trace_id}:{sp.span_id}"
                if key not in seen_source_keys:
                    seen_source_keys.add(key)
                    is_err = sp.status == "ERROR" or (sp.http_status_code and sp.http_status_code >= 500)
                    events.append(
                        TimelineEvent(
                            event_id=f"trace-span-{sp.id}",
                            event_type="TRACE_ERROR" if is_err else "TRACE_LATENCY",
                            timestamp=sp.timestamp_start,
                            title=f"Trace {'error' if is_err else 'latency concentration'} in {sp.service_name}",
                            summary=f"Span '{sp.operation_name}' on '{sp.service_name}' observed {sp.duration_ms:.1f}ms (status: {sp.status}).",
                            source_type=EvidenceSourceType.TRACE,
                            source_id=sp.trace_id,
                            metadata={
                                "trace_id": sp.trace_id,
                                "span_id": sp.span_id,
                                "service": sp.service_name,
                                "duration_ms": sp.duration_ms,
                                "status": sp.status,
                            },
                        )
                    )

        # Sort chronologically
        events.sort(key=lambda e: e.timestamp, reverse=not ascending)
        return events

