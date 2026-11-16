"""
Synthetic Telemetry Adapter.
Transforms internal synthetic demonstration metrics and events into normalized TelemetryRecords.
Preserves complete backward compatibility for demo and local development environments.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.telemetry.abstractions import TelemetryAdapter
from app.telemetry.normalizer import EnvironmentNormalizer, ServiceIdentityNormalizer
from app.telemetry.schemas import TelemetryEventType, TelemetryRecord, TelemetrySourceType


class SyntheticAdapter(TelemetryAdapter):
    """Adapter for internal synthetic demonstration data."""

    def validate(self, raw_data: Any) -> tuple[bool, list[str]]:
        """Validates synthetic data dictionary or list."""
        errors: list[str] = []
        if not isinstance(raw_data, (dict, list)):
            return False, ["Synthetic payload must be a JSON object or array of objects"]

        items = raw_data if isinstance(raw_data, list) else [raw_data]
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"Item #{idx}: Expected dict, received {type(item).__name__}")
                continue
            if "metric_name" not in item and "event_type" not in item:
                errors.append(f"Item #{idx}: Missing required 'metric_name' or 'event_type'")
            if "timestamp" not in item:
                errors.append(f"Item #{idx}: Missing required 'timestamp'")

        return len(errors) == 0, errors

    def normalize(self, raw_data: Any) -> list[TelemetryRecord]:
        """Normalizes synthetic metric/event dictionaries into TelemetryRecords."""
        items = raw_data if isinstance(raw_data, list) else [raw_data]
        records: list[TelemetryRecord] = []

        for item in items:
            raw_ts = item.get("timestamp")
            if isinstance(raw_ts, str):
                cleaned = raw_ts.replace("Z", "+00:00")
                ts = datetime.fromisoformat(cleaned)
            elif isinstance(raw_ts, datetime):
                ts = raw_ts
            else:
                ts = datetime.now(UTC)

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)

            # Determine event type
            is_metric = "metric_name" in item
            event_type = TelemetryEventType.METRIC if is_metric else TelemetryEventType.EVENT

            raw_service = (
                item.get("service")
                or item.get("dimension_data", {}).get("service")
                or "checkout-service"
            )
            canonical_service = ServiceIdentityNormalizer.normalize(raw_service)

            raw_env = (
                item.get("environment")
                or item.get("dimension_data", {}).get("environment")
                or "demo"
            )
            canonical_env = EnvironmentNormalizer.normalize(raw_env)

            record = TelemetryRecord(
                source=item.get("source", "synthetic-generator"),
                source_type=TelemetrySourceType.SYNTHETIC,
                event_type=event_type,
                timestamp=ts,
                service=canonical_service,
                environment=canonical_env,
                metric_name=item.get("metric_name"),
                value=float(item["value"]) if item.get("value") is not None else None,
                unit=item.get("unit", "count"),
                dimensions=item.get("dimension_data", {}),
                severity=item.get("severity", "INFO"),
                message=item.get("message"),
                metadata=item.get("event_metadata", {}),
                schema_version="1.0",
            )
            records.append(record)

        return records
