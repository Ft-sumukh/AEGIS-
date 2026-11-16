"""Service layer for querying, retrieving, and managing operational incidents."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.analytics.models import BusinessImpactEstimate, IncidentCandidate
from app.incidents.audit import IncidentAuditRecorder
from app.incidents.creation import IncidentCreationService
from app.incidents.evidence import IncidentEvidenceService
from app.incidents.impact import IncidentImpactService
from app.incidents.lifecycle import IncidentLifecycleManager
from app.incidents.timeline import IncidentTimelineService
from app.models.enums import EvidenceSourceType, IncidentStatus, SeverityLevel
from app.models.incident import Incident, IncidentEvidence, IncidentNote
from app.schemas.incident import (
    IncidentAcknowledgeRequest,
    IncidentCorrelationView,
    IncidentCreateManual,
    IncidentEvidenceCreate,
    IncidentFromCandidateRequest,
    IncidentImpactUpdateRequest,
    IncidentNoteCreate,
    IncidentStatusUpdate,
)


class IncidentService:
    """Encapsulates database operations for operational incidents."""

    @staticmethod
    def list_incidents(
        db: Session,
        company_id: uuid.UUID | None = None,
        severity: SeverityLevel | None = None,
        status: IncidentStatus | None = None,
        category: str | None = None,
        owner_id: str | None = None,
        team_name: str | None = None,
        search: str | None = None,
        sort_by: str = "detected_at",
        sort_desc: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """Query incidents with filtering, search, safe sorting, and pagination."""
        query = select(Incident)
        count_query = select(func.count(Incident.id))

        if company_id:
            query = query.where(Incident.company_id == company_id)
            count_query = count_query.where(Incident.company_id == company_id)

        if severity:
            query = query.where(Incident.severity == severity)
            count_query = count_query.where(Incident.severity == severity)

        if status:
            query = query.where(Incident.status == status)
            count_query = count_query.where(Incident.status == status)

        if category:
            query = query.where(Incident.category == category)
            count_query = count_query.where(Incident.category == category)

        if owner_id:
            query = query.where(Incident.owner_id == owner_id)
            count_query = count_query.where(Incident.owner_id == owner_id)

        if team_name:
            query = query.where(Incident.team_name == team_name)
            count_query = count_query.where(Incident.team_name == team_name)

        if search and search.strip():
            term = f"%{search.strip()}%"
            search_cond = or_(Incident.title.ilike(term), Incident.summary.ilike(term))
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)

        total = db.scalar(count_query) or 0

        # Safe sorting whitelist
        sort_column_map = {
            "detected_at": Incident.detected_at,
            "created_at": Incident.created_at,
            "severity": Incident.severity,
            "status": Incident.status,
            "estimated_revenue_impact": Incident.estimated_revenue_impact,
        }
        col = sort_column_map.get(sort_by, Incident.detected_at)
        order_clause = col.desc() if sort_desc else col.asc()

        items = db.scalars(query.order_by(order_clause).limit(limit).offset(offset)).all()
        return list(items), total

    @staticmethod
    def get_incident_by_id(db: Session, incident_id: uuid.UUID) -> Incident | None:
        """Retrieve a single incident by ID with eagerly loaded anomalies, evidence, and notes."""
        query = (
            select(Incident)
            .where(Incident.id == incident_id)
            .options(
                selectinload(Incident.anomalies),
                selectinload(Incident.evidence),
                selectinload(Incident.notes),
            )
        )
        return db.scalar(query)

    @staticmethod
    def create_manual(
        db: Session,
        payload: IncidentCreateManual,
        actor: str = "operator",
    ) -> Incident:
        """Creates a manual incident via the creation subsystem."""
        return IncidentCreationService.create_manual_incident(
            db=db,
            company_id=payload.company_id,
            title=payload.title,
            summary=payload.summary,
            severity=payload.severity,
            category=payload.category,
            affected_systems=payload.affected_systems,
            affected_metrics=payload.affected_metrics,
            tags=payload.tags,
            detected_at=payload.detected_at,
            owner_id=payload.owner_id,
            team_name=payload.team_name,
            initial_note=payload.initial_note,
            actor=actor,
        )

    @staticmethod
    def create_from_candidate(
        db: Session,
        payload: IncidentFromCandidateRequest,
        actor: str = "system",
    ) -> tuple[Incident, bool]:
        """Converts an API candidate payload into an IncidentCandidate domain object and creates the incident."""
        impact_est = BusinessImpactEstimate(
            estimated_revenue_impact=payload.estimated_revenue_impact,
            estimated_orders_affected=payload.orders_affected
            if hasattr(payload, "orders_affected")
            else payload.estimated_orders_affected,
            estimated_users_affected=payload.users_affected
            if hasattr(payload, "users_affected")
            else payload.estimated_users_affected,
            additional_support_tickets=payload.additional_support_tickets,
            additional_complaints=payload.additional_complaints,
            is_preliminary=True,
        )

        candidate = IncidentCandidate(
            candidate_id=payload.candidate_id,
            company_id=payload.company_id,
            title=payload.title,
            preliminary_summary=payload.preliminary_summary,
            severity=payload.severity,
            correlation_score=payload.correlation_score,
            first_detected_at=payload.first_detected_at,
            last_detected_at=payload.last_detected_at,
            affected_metrics=payload.affected_metrics,
            anomaly_ids=payload.anomaly_ids,
            impact=impact_est,
        )

        return IncidentCreationService.create_from_candidate(
            db=db,
            candidate=candidate,
            actor=actor,
        )

    @staticmethod
    def acknowledge_incident(
        db: Session,
        incident: Incident,
        payload: IncidentAcknowledgeRequest,
        actor: str = "operator",
    ) -> Incident:
        """Acknowledges an incident."""
        return IncidentLifecycleManager.acknowledge(
            db=db,
            incident=incident,
            actor=actor,
            transition_to_investigating=payload.transition_to_investigating,
        )

    @staticmethod
    def update_status(
        db: Session,
        incident: Incident,
        payload: IncidentStatusUpdate,
        actor: str = "operator",
    ) -> Incident:
        """Transitions an incident to a new lifecycle status."""
        return IncidentLifecycleManager.transition(
            db=db,
            incident=incident,
            new_status=payload.status,
            actor=actor,
            reason=payload.reason,
            resolution_summary=payload.resolution_summary,
            closed_by=payload.closed_by,
        )

    @staticmethod
    def add_evidence(
        db: Session,
        incident: Incident,
        payload: IncidentEvidenceCreate,
        actor: str = "operator",
    ) -> IncidentEvidence:
        """Attaches an evidence record to an incident."""
        return IncidentEvidenceService.add_evidence(
            db=db,
            incident_id=incident.id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            title=payload.title,
            summary=payload.summary,
            observed_at=payload.observed_at,
            metadata=payload.metadata,
            relevance_override=payload.relevance_override,
            severity=payload.severity,
            actor=actor,
            access_level=payload.access_level,
        )

    @staticmethod
    def list_evidence(
        db: Session,
        incident_id: uuid.UUID,
        source_type: EvidenceSourceType | None = None,
    ) -> list[IncidentEvidence]:
        """Lists evidence attached to an incident."""
        return IncidentEvidenceService.list_evidence(
            db=db, incident_id=incident_id, source_type=source_type
        )

    @staticmethod
    def add_note(
        db: Session,
        incident: Incident,
        payload: IncidentNoteCreate,
    ) -> IncidentNote:
        """Appends an operator note to an incident."""
        now = datetime.now(UTC)
        note = IncidentNote(
            id=uuid.uuid4(),
            incident_id=incident.id,
            author=payload.author.strip(),
            text=payload.text.strip(),
            created_at=now,
        )
        db.add(note)
        db.flush()

        IncidentAuditRecorder.record(
            db=db,
            action="NOTE_ADDED",
            incident_id=incident.id,
            company_id=incident.company_id,
            actor_id=payload.author.strip(),
            metadata={"note_id": str(note.id)},
        )
        return note

    @staticmethod
    def list_notes(
        db: Session,
        incident_id: uuid.UUID,
    ) -> list[IncidentNote]:
        """Lists notes for an incident ordered chronologically."""
        stmt = (
            select(IncidentNote)
            .where(IncidentNote.incident_id == incident_id)
            .order_by(IncidentNote.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_impact(
        db: Session,
        incident: Incident,
        payload: IncidentImpactUpdateRequest,
        actor: str = "operator",
    ) -> Incident:
        """Updates preliminary business impact."""
        service = IncidentImpactService()
        service.update_incident_impact(
            db=db,
            incident=incident,
            new_revenue=payload.revenue_impact,
            new_orders=payload.orders_affected,
            new_users=payload.users_affected,
            new_support=payload.support_impact,
            actor=actor,
        )
        return incident

    @staticmethod
    def get_timeline(
        db: Session,
        incident: Incident,
        ascending: bool = True,
        include_adjacent: bool = True,
    ) -> list[dict[str, Any]]:
        """Generates timeline events."""
        events = IncidentTimelineService.build_timeline(
            db=db,
            incident=incident,
            ascending=ascending,
            include_adjacent_events=include_adjacent,
        )
        return [e.to_dict() for e in events]

    @staticmethod
    def get_correlation_view(incident: Incident) -> IncidentCorrelationView:
        """Builds correlation summary view."""
        return IncidentCorrelationView(
            incident_id=incident.id,
            correlation_score=incident.confidence,
            candidate_id=incident.incident_metadata.get("candidate_id"),
            anomaly_count=len(incident.anomalies),
            evidence_count=len(incident.evidence),
            affected_metrics=incident.affected_metrics,
            affected_systems=incident.affected_systems,
            estimated_revenue_impact=float(incident.estimated_revenue_impact or 0.0),
            estimated_orders_affected=incident.estimated_orders_affected or 0,
        )
