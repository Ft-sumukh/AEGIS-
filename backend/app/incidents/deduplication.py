"""Deterministic deduplication service for operational incidents."""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.models import IncidentCandidate
from app.incidents.models import DeduplicationResult
from app.models.enums import IncidentStatus
from app.models.incident import Incident


class IncidentDeduplicator:
    """Generates deterministic fingerprints and identifies duplicate incident occurrences."""

    @staticmethod
    def generate_candidate_fingerprint(candidate: IncidentCandidate) -> str:
        """Computes deterministic SHA-256 fingerprint for an IncidentCandidate.

        Inputs:
        - company_id
        - sorted affected metrics list
        - 4-hour temporal window bucket
        """
        metrics_key = ",".join(sorted(set(candidate.affected_metrics)))
        # 4-hour temporal window bucket prevents micro-drift duplicate creation
        dt = candidate.first_detected_at
        time_bucket = f"{dt.strftime('%Y-%m-%d')}-b{dt.hour // 4}"
        raw_key = f"{candidate.company_id}:{metrics_key}:{time_bucket}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def generate_manual_fingerprint(
        company_id: uuid.UUID, title: str, detected_at: datetime
    ) -> str:
        """Computes deterministic fingerprint for an operator-created manual incident."""
        normalized_title = title.strip().lower()
        time_bucket = f"{detected_at.strftime('%Y-%m-%d')}-b{detected_at.hour // 4}"
        raw_key = f"{company_id}:manual:{normalized_title}:{time_bucket}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def evaluate(
        db: Session,
        company_id: uuid.UUID,
        fingerprint: str,
    ) -> DeduplicationResult:
        """Checks whether a non-closed incident with this fingerprint already exists."""
        stmt = (
            select(Incident)
            .where(
                Incident.company_id == company_id,
                Incident.fingerprint == fingerprint,
                Incident.status != IncidentStatus.CLOSED,
            )
            .limit(1)
        )
        existing = db.scalar(stmt)
        if existing:
            return DeduplicationResult(
                is_duplicate=True,
                fingerprint=fingerprint,
                existing_incident_id=existing.id,
            )

        return DeduplicationResult(
            is_duplicate=False,
            fingerprint=fingerprint,
            existing_incident_id=None,
        )
