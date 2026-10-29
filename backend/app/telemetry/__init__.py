"""
Aegis Telemetry Package.
Vendor-neutral observability and operational telemetry ingestion,
validation, sanitization, normalization, and deduplication foundation.
"""

from app.telemetry.abstractions import CircuitBreaker, TelemetryAdapter, TelemetrySource
from app.telemetry.normalizer import MetricNameNormalizer, ServiceIdentityNormalizer
from app.telemetry.schemas import (
    BatchTelemetryPayload,
    DataQualityMetrics,
    IngestionResult,
    SourceHealthStatus,
    TelemetryRecord,
    TelemetrySourceType,
)

__all__ = [
    "BatchTelemetryPayload",
    "CircuitBreaker",
    "DataQualityMetrics",
    "IngestionResult",
    "MetricNameNormalizer",
    "ServiceIdentityNormalizer",
    "SourceHealthStatus",
    "TelemetryAdapter",
    "TelemetryIngestionService",
    "TelemetryRecord",
    "TelemetrySource",
    "TelemetrySourceType",
]


def __getattr__(name: str):
    if name == "TelemetryIngestionService":
        from app.telemetry.service import TelemetryIngestionService
        return TelemetryIngestionService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

