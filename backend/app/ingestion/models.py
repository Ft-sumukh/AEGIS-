"""Ingestion models and structured reporting data contracts."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationErrorItem:
    """Individual data validation failure detail."""

    entity_type: str
    record_identifier: str
    field_name: str
    error_message: str
    rejected_value: Any = None


@dataclass
class EntityIngestionSummary:
    """Ingestion statistics for a single entity type."""

    entity_name: str
    received: int = 0
    inserted: int = 0
    rejected: int = 0
    duplicates: int = 0
    validation_errors: list[ValidationErrorItem] = field(default_factory=list)


@dataclass
class IngestionReport:
    """Comprehensive structured report for an ingestion pipeline run."""

    dataset_id: str
    data_source: str
    classification: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    total_records_received: int = 0
    total_records_inserted: int = 0
    total_records_rejected: int = 0
    total_duplicates_detected: int = 0
    entity_summaries: dict[str, EntityIngestionSummary] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts report to dictionary representation for logging and API serialization."""
        return {
            "dataset_id": self.dataset_id,
            "data_source": self.data_source,
            "classification": self.classification,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 3),
            "records_received": self.total_records_received,
            "records_inserted": self.total_records_inserted,
            "records_rejected": self.total_records_rejected,
            "duplicates_detected": self.total_duplicates_detected,
            "entities": {
                name: {
                    "received": summary.received,
                    "inserted": summary.inserted,
                    "rejected": summary.rejected,
                    "duplicates": summary.duplicates,
                    "validation_error_count": len(summary.validation_errors),
                }
                for name, summary in self.entity_summaries.items()
            },
            "errors": self.errors,
        }
