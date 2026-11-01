"""Evidence management, deterministic relevance scoring, and deduplication service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.incidents.audit import IncidentAuditRecorder
from app.incidents.severity import IncidentSeverityService
from app.models.enums import EvidenceSourceType, SeverityLevel
from app.models.incident import Incident, IncidentEvidence

logger = get_logger("aegis.incidents.evidence")


class IncidentEvidenceService:
    """Manages first-class evidence items attached to an incident with deterministic relevance scoring."""

    @staticmethod
    def calculate_relevance_score(
        source_type: EvidenceSourceType,
        observed_at: datetime,
        incident_detected_at: datetime,
        severity: SeverityLevel | None = None,
        is_direct_metric: bool = False,
    ) -> float:
        """Computes a deterministic, explainable system-assigned relevance score [0.10, 0.99]."""
        # 1. Base score by evidence source type
        base_scores = {
            EvidenceSourceType.ANOMALY: 0.90,
            EvidenceSourceType.DEPLOYMENT: 0.88,
            EvidenceSourceType.SYSTEM_EVENT: 0.85,
            EvidenceSourceType.CUSTOMER_COMPLAINT: 0.80,
            EvidenceSourceType.SUPPORT_TICKET: 0.75,
            EvidenceSourceType.METRIC: 0.75,
            EvidenceSourceType.MANUAL_NOTE: 0.70,
            EvidenceSourceType.DOCUMENT: 0.60,
        }
        score = base_scores.get(source_type, 0.70)

        # 2. Temporal proximity multiplier
        delta_seconds = abs((observed_at - incident_detected_at).total_seconds())
        delta_mins = delta_seconds / 60.0

        if delta_mins <= 30.0:
            time_factor = 1.0
        elif delta_mins <= 120.0:
            time_factor = 0.92
        elif delta_mins <= 360.0:
            time_factor = 0.82
        else:
            time_factor = max(0.50, 1.0 - (delta_mins / 1440.0))

        score *= time_factor

        # 3. Severity & direct relationship bonus
        if severity == SeverityLevel.CRITICAL:
            score += 0.08
        elif severity in (SeverityLevel.HIGH, SeverityLevel.ERROR):
            score += 0.04

        if is_direct_metric:
            score += 0.05

        return round(max(0.10, min(0.99, score)), 3)

    @classmethod
    def add_evidence(
        cls,
        db: Session,
        incident_id: uuid.UUID,
        source_type: EvidenceSourceType,
        source_id: str | None,
        title: str,
        summary: str,
        observed_at: datetime,
        metadata: dict[str, Any] | None = None,
        relevance_override: float | None = None,
        severity: SeverityLevel | None = None,
        actor: str = "system",
        access_level: str = "INTERNAL",
    ) -> IncidentEvidence:
        """Attaches an evidence record to an incident with deduplication and relevance scoring."""
        # 1. Fetch parent incident
        incident = db.get(Incident, incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} does not exist.")

        # 2. Deduplication check: do not attach the exact same source record twice
        if source_id:
            existing = db.scalar(
                select(IncidentEvidence).where(
                    IncidentEvidence.incident_id == incident_id,
                    IncidentEvidence.source_type == source_type,
                    IncidentEvidence.source_id == source_id,
                )
            )
            if existing:
                logger.debug(
                    f"Evidence {source_type.value}:{source_id} already attached to incident {incident_id}. Skipping duplicate."
                )
                return existing

        # 3. Calculate deterministic relevance score
        if relevance_override is not None:
            relevance = round(max(0.0, min(1.0, relevance_override)), 3)
        else:
            is_direct = False
            if source_type in (EvidenceSourceType.ANOMALY, EvidenceSourceType.METRIC):
                is_direct = any(m in title or m in summary for m in incident.affected_metrics)
            relevance = cls.calculate_relevance_score(
                source_type=source_type,
                observed_at=observed_at,
                incident_detected_at=incident.detected_at,
                severity=severity,
                is_direct_metric=is_direct,
            )

        # 4. Enrich metadata with access classification and system-assigned relevance explanation
        enriched_meta = dict(metadata or {})
        enriched_meta.update(
            {
                "access_level": access_level,  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
                "system_assigned_relevance": True,
                "relevance_explanation": (
                    f"System-assigned score {relevance:.2f} based on {source_type.value} "
                    f"type weight and temporal alignment with incident detection."
                ),
            }
        )

        evidence = IncidentEvidence(
            id=uuid.uuid4(),
            incident_id=incident_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            summary=summary,
            observed_at=observed_at,
            relevance_score=relevance,
            evidence_metadata=enriched_meta,
            created_at=datetime.now(UTC),
        )

        db.add(evidence)
        db.flush()

        # 5. Check potential severity escalation if new evidence indicates critical degradation
        if (
            severity
            and severity == SeverityLevel.CRITICAL
            and incident.severity != SeverityLevel.CRITICAL
        ):
            new_sev, new_reason, escalated = IncidentSeverityService.evaluate_escalation(
                current_severity=incident.severity,
                proposed_severity=SeverityLevel.CRITICAL,
                current_reason=incident.severity_reason,
                escalation_factor=f"Critical evidence attached ({title})",
            )
            if escalated:
                incident.severity = new_sev
                incident.severity_reason = new_reason
                IncidentAuditRecorder.record(
                    db=db,
                    action="INCIDENT_SEVERITY_CHANGED",
                    incident_id=incident_id,
                    company_id=incident.company_id,
                    actor_id=actor,
                    metadata={"new_severity": new_sev.value, "reason": new_reason},
                )

        # 6. Audit logging
        IncidentAuditRecorder.record(
            db=db,
            action="EVIDENCE_ADDED",
            incident_id=incident_id,
            company_id=incident.company_id,
            actor_id=actor,
            metadata={
                "evidence_id": str(evidence.id),
                "source_type": source_type.value,
                "source_id": source_id,
                "relevance_score": relevance,
            },
        )

        return evidence

    @staticmethod
    def list_evidence(
        db: Session,
        incident_id: uuid.UUID,
        source_type: EvidenceSourceType | None = None,
    ) -> list[IncidentEvidence]:
        """Queries all evidence for an incident ordered by relevance score descending."""
        stmt = select(IncidentEvidence).where(IncidentEvidence.incident_id == incident_id)
        if source_type:
            stmt = stmt.where(IncidentEvidence.source_type == source_type)

        stmt = stmt.order_by(
            IncidentEvidence.relevance_score.desc(),
            IncidentEvidence.observed_at.asc(),
        )
        return list(db.scalars(stmt).all())
