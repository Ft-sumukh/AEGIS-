"""Aegis Incident Management, Correlation & Evidence subsystem."""

from app.incidents.audit import IncidentAuditRecorder
from app.incidents.creation import IncidentCreationService
from app.incidents.deduplication import IncidentDeduplicator
from app.incidents.evidence import IncidentEvidenceService
from app.incidents.impact import IncidentImpactService
from app.incidents.lifecycle import IncidentLifecycleManager
from app.incidents.models import (
    DeduplicationResult,
    ImpactDelta,
    InvalidLifecycleTransitionError,
    TimelineEvent,
)
from app.incidents.severity import SEVERITY_RANK, IncidentSeverityService
from app.incidents.timeline import IncidentTimelineService

__all__ = [
    "DeduplicationResult",
    "ImpactDelta",
    "IncidentAuditRecorder",
    "IncidentCreationService",
    "IncidentDeduplicator",
    "IncidentEvidenceService",
    "IncidentImpactService",
    "IncidentLifecycleManager",
    "IncidentSeverityService",
    "IncidentTimelineService",
    "InvalidLifecycleTransitionError",
    "SEVERITY_RANK",
    "TimelineEvent",
]
