"""Incident creation service supporting automated creation from candidate and manual creation."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.models import IncidentCandidate
from app.core.logging import get_logger
from app.incidents.audit import IncidentAuditRecorder
from app.incidents.deduplication import IncidentDeduplicator
from app.incidents.evidence import IncidentEvidenceService
from app.incidents.severity import IncidentSeverityService
from app.models.anomaly import Anomaly
from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.events import Deployment
from app.models.incident import Incident, IncidentNote

logger = get_logger("aegis.incidents.creation")


def infer_category_and_systems(metrics: list[str]) -> tuple[str, list[str]]:
    """Deterministically infers primary category and affected systems from metric names."""
    joined = " ".join(metrics).lower()
    if any(k in joined for k in ("checkout", "cart", "payment", "order")):
        return "CHECKOUT", ["checkout-service", "payment-service", "order-processing"]
    if any(k in joined for k in ("api", "latency", "5xx", "request", "endpoint")):
        return "API", ["api-gateway", "web-application"]
    if any(k in joined for k in ("db", "database", "query", "sql", "pool", "connection")):
        return "DATABASE", ["postgres-cluster", "connection-pool"]
    if any(k in joined for k in ("auth", "login", "session", "token")):
        return "AUTHENTICATION", ["auth-service", "identity-provider"]
    if any(k in joined for k in ("network", "dns", "traffic", "ingress")):
        return "INFRASTRUCTURE", ["ingress-router", "network-layer"]
    return "SYSTEM_DEGRADATION", ["operational-stack"]


class IncidentCreationService:
    """Creates structured operational incidents from deterministic candidates or manual inputs."""

    @classmethod
    def create_from_candidate(
        cls,
        db: Session,
        candidate: IncidentCandidate,
        actor: str = "system",
    ) -> tuple[Incident, bool]:
        """Converts an IncidentCandidate into a persisted, correlated Incident entity.

        Returns:
            tuple[Incident, bool]: (Incident, is_newly_created)
        """
        fingerprint = IncidentDeduplicator.generate_candidate_fingerprint(candidate)
        dedup_result = IncidentDeduplicator.evaluate(db, candidate.company_id, fingerprint)

        if dedup_result.is_duplicate and dedup_result.existing_incident_id:
            logger.info(
                f"Candidate {candidate.candidate_id} matches existing active incident {dedup_result.existing_incident_id}. Deduplicating."
            )
            existing_incident = db.get(Incident, dedup_result.existing_incident_id)
            if existing_incident:
                # Associate any newly discovered anomalies not yet linked
                existing_anomaly_ids = {a.id for a in existing_incident.anomalies}
                new_anomaly_ids = [
                    aid for aid in candidate.anomaly_ids if aid not in existing_anomaly_ids
                ]
                if new_anomaly_ids:
                    stmt = select(Anomaly).where(Anomaly.id.in_(new_anomaly_ids))
                    new_anomalies = list(db.scalars(stmt).all())
                    existing_incident.anomalies.extend(new_anomalies)
                    for anom in new_anomalies:
                        IncidentEvidenceService.add_evidence(
                            db=db,
                            incident_id=existing_incident.id,
                            source_type=EvidenceSourceType.ANOMALY,
                            source_id=str(anom.id),
                            title=f"Correlated anomaly: {anom.metric_name}",
                            summary=f"Detected abnormal value {anom.actual_value} (deviation: {anom.deviation_score:.2f}σ).",
                            observed_at=anom.detected_at,
                            severity=anom.severity,
                            actor=actor,
                        )
                return existing_incident, False

        # Query all correlated anomalies from candidate
        anomalies: list[Anomaly] = []
        if candidate.anomaly_ids:
            stmt = select(Anomaly).where(Anomaly.id.in_(candidate.anomaly_ids))
            anomalies = list(db.scalars(stmt).all())

        category, systems = infer_category_and_systems(candidate.affected_metrics)
        rev_impact = float(candidate.impact.estimated_revenue_impact)
        orders_impact = candidate.impact.estimated_orders_affected

        # Deterministic severity calculation
        severity, severity_reason = IncidentSeverityService.calculate_initial_severity(
            anomalies=anomalies,
            affected_metrics=candidate.affected_metrics,
            revenue_impact=rev_impact,
            orders_affected=orders_impact,
        )

        now = datetime.now(UTC)
        summary = (
            f"Operational anomalies detected across {len(candidate.affected_metrics)} metrics: "
            f"{', '.join(sorted(candidate.affected_metrics))}. "
            f"First observed degradation at {candidate.first_detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"Deterministic correlation confidence: {candidate.correlation_score:.2f}."
        )

        incident = Incident(
            id=uuid.uuid4(),
            company_id=candidate.company_id,
            title=candidate.title,
            summary=summary,
            severity=severity,
            severity_reason=severity_reason,
            status=IncidentStatus.OPEN,
            category=category,
            tags=["automated-detection", "deterministic-correlation"],
            affected_systems=systems,
            affected_metrics=candidate.affected_metrics,
            detected_at=candidate.first_detected_at,
            confidence=round(candidate.correlation_score, 3),
            estimated_revenue_impact=Decimal(str(round(rev_impact, 2))),
            estimated_orders_affected=orders_impact,
            estimated_users_affected=candidate.impact.estimated_users_affected,
            estimated_support_impact=(
                candidate.impact.additional_support_tickets + candidate.impact.additional_complaints
            ),
            fingerprint=fingerprint,
            incident_metadata={
                "candidate_id": str(candidate.candidate_id),
                "correlation_score": candidate.correlation_score,
                "status_history": [],
                "impact_history": [],
            },
            created_at=now,
            updated_at=now,
        )

        # Associate anomalies
        incident.anomalies.extend(anomalies)
        db.add(incident)
        db.flush()

        # Attach initial evidence from anomalies
        for anom in anomalies:
            IncidentEvidenceService.add_evidence(
                db=db,
                incident_id=incident.id,
                source_type=EvidenceSourceType.ANOMALY,
                source_id=str(anom.id),
                title=f"Anomaly: {anom.metric_name}",
                summary=f"Deviation of {anom.deviation:.2f}σ observed (observed: {anom.observed_value}, expected: {anom.expected_value}).",
                observed_at=anom.detected_at,
                severity=anom.severity,
                actor=actor,
            )

        # Correlate adjacent deployments within 2 hours prior as evidence
        dep_stmt = (
            select(Deployment)
            .where(
                Deployment.company_id == candidate.company_id,
                Deployment.deployed_at >= candidate.first_detected_at - timedelta(hours=2),
                Deployment.deployed_at <= candidate.first_detected_at + timedelta(minutes=15),
            )
            .order_by(Deployment.deployed_at.desc())
        )
        recent_deployments = db.scalars(dep_stmt).all()
        for dep in recent_deployments:
            IncidentEvidenceService.add_evidence(
                db=db,
                incident_id=incident.id,
                source_type=EvidenceSourceType.DEPLOYMENT,
                source_id=str(dep.id),
                title=f"Deployment of {dep.service} ({dep.version})",
                summary=f"Service {dep.service} version {dep.version} was deployed shortly before observed degradation.",
                observed_at=dep.deployed_at,
                actor=actor,
            )

        # Record creation audit log
        IncidentAuditRecorder.record(
            db=db,
            action="INCIDENT_CREATED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata={
                "creation_mode": "FROM_CANDIDATE",
                "candidate_id": str(candidate.candidate_id),
                "severity": severity.value,
                "affected_metrics": candidate.affected_metrics,
            },
        )

        db.flush()
        logger.info(
            f"Created operational incident {incident.id} ('{incident.title}') with severity {severity.value}"
        )

        try:
            from app.core.events import broadcast_event_sync

            broadcast_event_sync(
                event_type="INCIDENT_CREATED",
                payload={
                    "incident_id": str(incident.id),
                    "title": incident.title,
                    "severity": severity.value,
                    "affected_systems": incident.affected_systems,
                    "revenue_impact": float(incident.estimated_revenue_impact or 0),
                },
                company_id=str(incident.company_id),
            )
        except Exception:
            pass

        return incident, True

    @classmethod
    def create_manual_incident(
        cls,
        db: Session,
        company_id: uuid.UUID,
        title: str,
        summary: str,
        severity: SeverityLevel = SeverityLevel.MEDIUM,
        category: str | None = None,
        affected_systems: list[str] | None = None,
        affected_metrics: list[str] | None = None,
        tags: list[str] | None = None,
        detected_at: datetime | None = None,
        owner_id: str | None = None,
        team_name: str | None = None,
        initial_note: str | None = None,
        actor: str = "operator",
    ) -> Incident:
        """Creates an incident manually initiated by an operator."""
        now = datetime.now(UTC)
        det_at = detected_at or now
        fingerprint = IncidentDeduplicator.generate_manual_fingerprint(company_id, title, det_at)

        systems = affected_systems or []
        metrics = affected_metrics or []
        if not category:
            category, inferred_sys = infer_category_and_systems(metrics)
            if not systems:
                systems = inferred_sys

        incident = Incident(
            id=uuid.uuid4(),
            company_id=company_id,
            title=title.strip(),
            summary=summary.strip(),
            severity=severity,
            severity_reason=f"Operator '{actor}' declared incident with severity {severity.value}.",
            status=IncidentStatus.OPEN,
            category=category,
            tags=tags or ["manual-creation"],
            affected_systems=systems,
            affected_metrics=metrics,
            detected_at=det_at,
            owner_id=owner_id,
            team_name=team_name,
            fingerprint=fingerprint,
            incident_metadata={
                "creation_mode": "MANUAL",
                "created_by": actor,
                "status_history": [],
                "impact_history": [],
            },
            created_at=now,
            updated_at=now,
        )

        db.add(incident)
        db.flush()

        if initial_note and initial_note.strip():
            note = IncidentNote(
                id=uuid.uuid4(),
                incident_id=incident.id,
                author=actor,
                text=initial_note.strip(),
                created_at=now,
            )
            db.add(note)
            db.flush()

        IncidentAuditRecorder.record(
            db=db,
            action="INCIDENT_CREATED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata={"creation_mode": "MANUAL", "severity": severity.value},
        )

        db.flush()
        logger.info(
            f"Operator '{actor}' created manual incident {incident.id} ('{incident.title}')"
        )

        try:
            from app.core.events import broadcast_event_sync

            broadcast_event_sync(
                event_type="INCIDENT_CREATED",
                payload={
                    "incident_id": str(incident.id),
                    "title": incident.title,
                    "severity": severity.value,
                    "affected_systems": incident.affected_systems,
                    "revenue_impact": float(incident.estimated_revenue_impact or 0),
                },
                company_id=str(incident.company_id),
            )
        except Exception:
            pass

        return incident
