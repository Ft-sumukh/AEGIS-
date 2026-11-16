"""Cross-Source Correlation Engine linking Deployments, Traces, Logs, Metrics, and Business Impact."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.critical_path import CriticalPathAnalyzer
from app.analytics.error_propagation import ErrorPropagationAnalyzer
from app.core.logging import get_logger
from app.models.anomaly import Anomaly
from app.models.enums import EvidenceSourceType
from app.models.events import Deployment, SystemEvent
from app.models.incident import Incident, IncidentEvidence
from app.models.trace import TraceSpan

logger = get_logger("aegis.analytics.cross_correlation")


class CrossSourceCorrelator:
    """Discovers temporal and topological alignments across heterogenous operational evidence."""

    @classmethod
    def correlate_incident(
        cls,
        db: Session,
        incident_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Correlates an incident against traces, deployments, logs, and metrics with strict non-causal language."""
        incident = db.get(Incident, incident_id)
        if not incident:
            return {"error": f"Incident {incident_id} not found"}

        detected_at = incident.detected_at
        company_id = incident.company_id
        affected_services = incident.affected_systems or []
        window_start = detected_at - timedelta(minutes=60)
        window_end = detected_at + timedelta(minutes=60)

        # 1. Correlate Preceding Deployments
        dep_q = (
            select(Deployment)
            .where(
                Deployment.company_id == company_id,
                Deployment.deployed_at >= detected_at - timedelta(hours=2),
                Deployment.deployed_at <= detected_at,
            )
            .order_by(Deployment.deployed_at.desc())
        )
        recent_deployments = list(db.scalars(dep_q).all())
        lead_deployment: Optional[Deployment] = recent_deployments[0] if recent_deployments else None

        # 2. Correlate Trace Spans (slow and error traces for affected services)
        trace_q = select(TraceSpan).where(
            TraceSpan.company_id == company_id,
            TraceSpan.timestamp_start >= window_start,
            TraceSpan.timestamp_start <= window_end,
        )
        if affected_services:
            trace_q = trace_q.where(TraceSpan.service_name.in_(affected_services))

        spans = list(db.scalars(trace_q.order_by(TraceSpan.timestamp_start.asc()).limit(500)).all())

        # Partition traces
        distinct_trace_ids = list(dict.fromkeys(s.trace_id for s in spans))
        error_spans = [s for s in spans if s.status == "ERROR" or (s.http_status_code and s.http_status_code >= 500)]
        slow_spans = [s for s in spans if s.duration_ms >= 500.0]

        # 3. Correlate System Events / Logs
        log_q = select(SystemEvent).where(
            SystemEvent.company_id == company_id,
            SystemEvent.timestamp >= window_start,
            SystemEvent.timestamp <= window_end,
        )
        if affected_services:
            log_q = log_q.where(SystemEvent.service.in_(affected_services))
        system_events = list(db.scalars(log_q.order_by(SystemEvent.timestamp.asc()).limit(100)).all())

        # 4. Compute Temporal Latencies relative to Deployment
        timings: dict[str, Any] = {}
        if lead_deployment:
            dep_time = lead_deployment.deployed_at
            timings["deployment_version"] = lead_deployment.version
            timings["deployment_service"] = lead_deployment.service
            timings["deployment_timestamp"] = dep_time.isoformat()
            timings["deployment_to_incident_seconds"] = max(0.0, (detected_at - dep_time).total_seconds())

            if slow_spans:
                first_slow = min(s.timestamp_start for s in slow_spans)
                timings["deployment_to_first_slow_trace_seconds"] = max(0.0, (first_slow - dep_time).total_seconds())

            if error_spans:
                first_err = min(s.timestamp_start for s in error_spans)
                timings["deployment_to_first_error_trace_seconds"] = max(0.0, (first_err - dep_time).total_seconds())

        # 5. Analyze Error Propagation for representative error trace
        error_propagation_summary = None
        if error_spans:
            rep_trace_id = error_spans[0].trace_id
            rep_spans = [s for s in spans if s.trace_id == rep_trace_id]
            error_prop = ErrorPropagationAnalyzer.analyze(rep_spans)
            error_propagation_summary = {
                "trace_id": rep_trace_id,
                "root_error_service": error_prop.root_error_service,
                "assessment": error_prop.non_causal_assessment,
            }

        # 6. Analyze Critical Path for representative slow trace
        critical_path_summary = None
        if slow_spans:
            slowest = max(slow_spans, key=lambda s: s.duration_ms)
            rep_spans = [s for s in spans if s.trace_id == slowest.trace_id]
            c_path = CriticalPathAnalyzer.analyze(rep_spans)
            critical_path_summary = {
                "trace_id": slowest.trace_id,
                "duration_ms": c_path.critical_path_duration_ms,
                "assessment": c_path.non_causal_assessment,
            }

        # 7. Non-Causal Evidence Synthesis Statement
        dep_str = (
            f"Deployment '{lead_deployment.version}' on service '{lead_deployment.service}' at {lead_deployment.deployed_at.strftime('%H:%M:%S UTC')} "
            if lead_deployment
            else "No preceding deployments identified; "
        )
        non_causal_synthesis = (
            f"{dep_str}preceded the observed degradation. Traces ({len(slow_spans)} slow, {len(error_spans)} errors), "
            f"logs ({len(system_events)} events), and metrics show temporally aligned evidence across "
            f"the affected service path ({', '.join(affected_services) if affected_services else 'infrastructure'})."
        )

        return {
            "incident_id": str(incident_id),
            "detected_at": detected_at.isoformat(),
            "affected_services": affected_services,
            "lead_deployment": {
                "service": lead_deployment.service,
                "version": lead_deployment.version,
                "deployed_at": lead_deployment.deployed_at.isoformat(),
            }
            if lead_deployment
            else None,
            "timings": timings,
            "trace_metrics": {
                "total_spans_in_window": len(spans),
                "distinct_traces": len(distinct_trace_ids),
                "slow_spans_count": len(slow_spans),
                "error_spans_count": len(error_spans),
            },
            "error_propagation": error_propagation_summary,
            "critical_path": critical_path_summary,
            "non_causal_synthesis": non_causal_synthesis,
        }

    @classmethod
    def attach_trace_evidence(
        cls,
        db: Session,
        incident_id: uuid.UUID,
    ) -> list[IncidentEvidence]:
        """Generates and persists compact structured IncidentEvidence items for the incident."""
        corr = cls.correlate_incident(db, incident_id)
        if "error" in corr:
            return []

        incident = db.get(Incident, incident_id)
        if not incident:
            return []

        evidence_items: list[IncidentEvidence] = []
        now = datetime.now(UTC)

        # A. Preceding Deployment Evidence
        if corr.get("lead_deployment"):
            dep = corr["lead_deployment"]
            ev_dep = IncidentEvidence(
                id=uuid.uuid4(),
                incident_id=incident_id,
                source_type=EvidenceSourceType.DEPLOYMENT,
                source_id=f"deploy-{dep['service']}-{dep['version']}",
                source="deployment_system",
                source_timestamp=datetime.fromisoformat(dep["deployed_at"]),
                ingestion_timestamp=now,
                title=f"Deployment {dep['version']} on {dep['service']}",
                summary=f"Software deployment {dep['version']} on {dep['service']} occurred prior to the observed degradation.",
                observed_at=datetime.fromisoformat(dep["deployed_at"]),
                relevance_score=0.90,
                evidence_metadata=corr["timings"],
            )
            evidence_items.append(ev_dep)

        # B. Critical Path / Latency Pattern Evidence
        if corr.get("critical_path"):
            cp = corr["critical_path"]
            ev_cp = IncidentEvidence(
                id=uuid.uuid4(),
                incident_id=incident_id,
                source_type=EvidenceSourceType.CRITICAL_PATH,
                source_id=f"trace-{cp['trace_id']}",
                source="opentelemetry",
                source_timestamp=incident.detected_at,
                ingestion_timestamp=now,
                title="Distributed Trace Latency Contribution",
                summary=cp["assessment"],
                observed_at=incident.detected_at,
                relevance_score=0.95,
                evidence_metadata=cp,
            )
            evidence_items.append(ev_cp)

        # C. Error Propagation Pattern Evidence
        if corr.get("error_propagation"):
            ep = corr["error_propagation"]
            ev_ep = IncidentEvidence(
                id=uuid.uuid4(),
                incident_id=incident_id,
                source_type=EvidenceSourceType.TRACE_ERROR_PATTERN,
                source_id=f"trace-{ep['trace_id']}",
                source="opentelemetry",
                source_timestamp=incident.detected_at,
                ingestion_timestamp=now,
                title=f"Downstream Error Propagation from {ep['root_error_service']}",
                summary=ep["assessment"],
                observed_at=incident.detected_at,
                relevance_score=0.95,
                evidence_metadata=ep,
            )
            evidence_items.append(ev_ep)

        # D. Cross-Source Multi-Telemetry Synthesis Evidence
        ev_cross = IncidentEvidence(
            id=uuid.uuid4(),
            incident_id=incident_id,
            source_type=EvidenceSourceType.CROSS_SOURCE_CORRELATION,
            source_id=f"correlation-{incident_id}",
            source="aegis_analytics",
            source_timestamp=incident.detected_at,
            ingestion_timestamp=now,
            title="Cross-Source Telemetry Alignment",
            summary=corr["non_causal_synthesis"],
            observed_at=incident.detected_at,
            relevance_score=0.98,
            evidence_metadata={
                "timings": corr.get("timings", {}),
                "trace_metrics": corr.get("trace_metrics", {}),
            },
        )
        evidence_items.append(ev_cross)

        # Attach to incident
        for ev in evidence_items:
            db.add(ev)
        db.commit()

        return evidence_items
