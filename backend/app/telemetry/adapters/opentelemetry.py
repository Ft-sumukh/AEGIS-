"""
OpenTelemetry (OTel) Observability Adapter.
Normalizes OpenTelemetry OTLP JSON metrics, logs, and span records into Aegis TelemetryRecords.
Preserves W3C distributed trace context (trace_id, span_id, parent_span_id).
"""

from datetime import UTC, datetime
from typing import Any, Optional

from app.core.logging import get_logger
from app.telemetry.abstractions import TelemetryAdapter
from app.telemetry.normalizer import EnvironmentNormalizer, MetricNameNormalizer, ServiceIdentityNormalizer
from app.telemetry.schemas import (
    TelemetryEventType,
    TelemetryRecord,
    TelemetrySourceType,
)

logger = get_logger("aegis.telemetry.adapters.opentelemetry")


def _nano_to_datetime(nano_ts: Any) -> datetime:
    """Converts nanosecond integer/string timestamp to timezone-aware UTC datetime."""
    try:
        val = int(nano_ts)
        # Nanoseconds to seconds
        seconds = val / 1_000_000_000.0
        return datetime.fromtimestamp(seconds, tz=UTC)
    except Exception:
        return datetime.now(UTC)


def _extract_attributes(attrs_list: Any) -> dict[str, Any]:
    """Flattens OTLP key-value attribute lists into standard dictionary."""
    flattened: dict[str, Any] = {}
    if not isinstance(attrs_list, list):
        return flattened

    for item in attrs_list:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not key:
            continue
        val_obj = item.get("value", {})
        if isinstance(val_obj, dict):
            # OTLP values can be stringValue, intValue, doubleValue, boolValue
            val = (
                val_obj.get("stringValue")
                or val_obj.get("intValue")
                or val_obj.get("doubleValue")
                or val_obj.get("boolValue")
            )
            flattened[key] = val
        else:
            flattened[key] = val_obj

    return flattened


class OpenTelemetryAdapter(TelemetryAdapter):
    """Normalizes OpenTelemetry OTLP JSON structures (metrics, logs, traces)."""

    def validate(self, raw_data: Any) -> tuple[bool, list[str]]:
        """Validates incoming OTel payload."""
        errors: list[str] = []
        if not isinstance(raw_data, dict):
            return False, ["OTel payload must be a JSON object"]

        # Recognized top-level keys in OTLP JSON or simplified OTel format
        has_metrics = "resourceMetrics" in raw_data
        has_logs = "resourceLogs" in raw_data
        has_spans = "resourceSpans" in raw_data
        has_direct_events = "events" in raw_data

        if not (has_metrics or has_logs or has_spans or has_direct_events):
            errors.append(
                "Payload does not contain recognized OTel structures ('resourceMetrics', 'resourceLogs', 'resourceSpans', or 'events')"
            )

        return len(errors) == 0, errors

    def normalize(self, raw_data: Any) -> list[TelemetryRecord]:
        """Parses OTLP data and outputs normalized TelemetryRecord instances."""
        records: list[TelemetryRecord] = []

        # 1. Process Metrics (resourceMetrics)
        if "resourceMetrics" in raw_data:
            records.extend(self._parse_resource_metrics(raw_data["resourceMetrics"]))

        # 2. Process Logs (resourceLogs)
        if "resourceLogs" in raw_data:
            records.extend(self._parse_resource_logs(raw_data["resourceLogs"]))

        # 3. Process Spans/Traces (resourceSpans)
        if "resourceSpans" in raw_data:
            records.extend(self._parse_resource_spans(raw_data["resourceSpans"]))

        # 4. Process simplified OTel event list (if provided via direct batch endpoint)
        if "events" in raw_data and isinstance(raw_data["events"], list):
            for ev in raw_data["events"]:
                if isinstance(ev, dict):
                    rec = self._normalize_single_otel_event(ev)
                    if rec:
                        records.append(rec)

        return records

    def _parse_resource_metrics(self, resource_metrics: list[Any]) -> list[TelemetryRecord]:
        records: list[TelemetryRecord] = []
        for rm in resource_metrics:
            if not isinstance(rm, dict):
                continue
            res_attrs = _extract_attributes(rm.get("resource", {}).get("attributes", []))
            service = ServiceIdentityNormalizer.normalize(res_attrs.get("service.name", "otel-service"))
            env = EnvironmentNormalizer.normalize(res_attrs.get("deployment.environment", "production"))
            host = res_attrs.get("host.name") or res_attrs.get("k8s.pod.name")

            for sm in rm.get("scopeMetrics", []):
                for metric in sm.get("metrics", []):
                    metric_name = metric.get("name", "otel_metric")
                    unit = metric.get("unit", "")
                    normalized_name = MetricNameNormalizer.normalize(metric_name)

                    # Extract data points from gauge / sum / histogram
                    data_points = []
                    if "gauge" in metric:
                        data_points = metric["gauge"].get("dataPoints", [])
                    elif "sum" in metric:
                        data_points = metric["sum"].get("dataPoints", [])
                    elif "histogram" in metric:
                        data_points = metric["histogram"].get("dataPoints", [])

                    for dp in data_points:
                        dp_attrs = _extract_attributes(dp.get("attributes", []))
                        dp_attrs.update(res_attrs)
                        val = dp.get("asDouble") or dp.get("asInt") or dp.get("sum") or 0.0
                        ts = _nano_to_datetime(dp.get("timeUnixNano", 0))

                        rec = TelemetryRecord(
                            source="opentelemetry",
                            source_type=TelemetrySourceType.OTEL,
                            event_type=TelemetryEventType.METRIC,
                            timestamp=ts,
                            service=service,
                            environment=env,
                            host=host,
                            metric_name=normalized_name,
                            value=float(val),
                            unit=unit or "ms" if "latency" in normalized_name else "count",
                            dimensions=dp_attrs,
                            severity="INFO",
                            metadata={"otel_metric_original": metric_name},
                            schema_version="1.0",
                        )
                        records.append(rec)
        return records

    def _parse_resource_logs(self, resource_logs: list[Any]) -> list[TelemetryRecord]:
        records: list[TelemetryRecord] = []
        for rl in resource_logs:
            if not isinstance(rl, dict):
                continue
            res_attrs = _extract_attributes(rl.get("resource", {}).get("attributes", []))
            service = ServiceIdentityNormalizer.normalize(res_attrs.get("service.name", "otel-service"))
            env = EnvironmentNormalizer.normalize(res_attrs.get("deployment.environment", "production"))

            for sl in rl.get("scopeLogs", []):
                for log_record in sl.get("logRecords", []):
                    ts = _nano_to_datetime(log_record.get("timeUnixNano", 0))
                    sev = log_record.get("severityText", "INFO").upper()
                    body = log_record.get("body", {})
                    msg = body.get("stringValue") if isinstance(body, dict) else str(body)

                    trace_id = log_record.get("traceId")
                    span_id = log_record.get("spanId")

                    rec = TelemetryRecord(
                        source="opentelemetry",
                        source_type=TelemetrySourceType.OTEL,
                        event_type=TelemetryEventType.LOG,
                        timestamp=ts,
                        service=service,
                        environment=env,
                        severity=sev if sev in ["INFO", "WARN", "ERROR", "CRITICAL"] else "INFO",
                        message=msg,
                        trace_id=trace_id,
                        span_id=span_id,
                        dimensions=res_attrs,
                        schema_version="1.0",
                    )
                    records.append(rec)
        return records

    def _parse_resource_spans(self, resource_spans: list[Any]) -> list[TelemetryRecord]:
        records: list[TelemetryRecord] = []
        for rs in resource_spans:
            if not isinstance(rs, dict):
                continue
            res_attrs = _extract_attributes(rs.get("resource", {}).get("attributes", []))
            service = ServiceIdentityNormalizer.normalize(res_attrs.get("service.name", "otel-service"))
            env = EnvironmentNormalizer.normalize(res_attrs.get("deployment.environment", "production"))

            for ss in rs.get("scopeSpans", []):
                for span in ss.get("spans", []):
                    start_ts = _nano_to_datetime(span.get("startTimeUnixNano", 0))
                    end_ts = _nano_to_datetime(span.get("endTimeUnixNano", 0))
                    duration_ms = (end_ts - start_ts).total_seconds() * 1000.0

                    trace_id = span.get("traceId")
                    span_id = span.get("spanId")
                    parent_span_id = span.get("parentSpanId")
                    span_name = span.get("name", "span")
                    span_status = span.get("status", {}).get("code", "STATUS_CODE_UNSET")

                    is_error = span_status in ("STATUS_CODE_ERROR", 2, "ERROR")

                    rec = TelemetryRecord(
                        source="opentelemetry",
                        source_type=TelemetrySourceType.OTEL,
                        event_type=TelemetryEventType.TRACE,
                        timestamp=start_ts,
                        service=service,
                        environment=env,
                        metric_name="api_latency",
                        value=round(duration_ms, 2),
                        unit="ms",
                        severity="ERROR" if is_error else "INFO",
                        message=f"Span '{span_name}' (status: {span_status})",
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_span_id=parent_span_id,
                        dimensions={"span_name": span_name, "status_code": span_status},
                        schema_version="1.0",
                    )
                    records.append(rec)
        return records

    def _normalize_single_otel_event(self, item: dict[str, Any]) -> Optional[TelemetryRecord]:
        """Normalizes a single simplified dictionary event."""
        raw_service = item.get("service") or item.get("service_name") or "otel-service"
        service = ServiceIdentityNormalizer.normalize(raw_service)
        env = EnvironmentNormalizer.normalize(item.get("environment"))

        raw_ts = item.get("timestamp") or item.get("time")
        if isinstance(raw_ts, str):
            cleaned = raw_ts.replace("Z", "+00:00")
            ts = datetime.fromisoformat(cleaned)
        elif isinstance(raw_ts, (int, float)):
            ts = datetime.fromtimestamp(raw_ts if raw_ts < 1e11 else raw_ts / 1000.0, tz=UTC)
        else:
            ts = datetime.now(UTC)

        raw_metric = item.get("metric_name") or item.get("name")
        normalized_metric = MetricNameNormalizer.normalize(raw_metric) if raw_metric else None

        return TelemetryRecord(
            source=item.get("source", "opentelemetry"),
            source_type=TelemetrySourceType.OTEL,
            event_type=TelemetryEventType(item.get("event_type", "METRIC")),
            timestamp=ts,
            service=service,
            environment=env,
            metric_name=normalized_metric,
            value=float(item["value"]) if item.get("value") is not None else None,
            unit=item.get("unit", "ms"),
            dimensions=item.get("dimensions") or item.get("attributes") or {},
            severity=item.get("severity", "INFO"),
            message=item.get("message"),
            trace_id=item.get("trace_id") or item.get("traceId"),
            span_id=item.get("span_id") or item.get("spanId"),
            parent_span_id=item.get("parent_span_id") or item.get("parentSpanId"),
            schema_version="1.0",
        )
