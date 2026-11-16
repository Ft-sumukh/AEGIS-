"""Trace Normalization and Sanitization Engine for Distributed Traces."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from app.core.logging import get_logger
from app.security.sanitizer import SENSITIVE_DICT_KEYS, DataSanitizer
from app.telemetry.normalizer import EnvironmentNormalizer, ServiceIdentityNormalizer
from app.telemetry.trace_schemas import NormalizedSpanRecord

logger = get_logger("aegis.telemetry.trace_normalizer")

# Allowlist of operationally safe attribute prefixes and keys
SAFE_ATTRIBUTE_KEYS = {
    "service.name",
    "service.version",
    "deployment.environment",
    "http.method",
    "http.route",
    "http.status_code",
    "http.target",
    "http.flavor",
    "http.scheme",
    "http.host",
    "rpc.system",
    "rpc.service",
    "rpc.method",
    "rpc.grpc.status_code",
    "db.system",
    "db.operation",
    "db.name",
    "peer.service",
    "net.peer.name",
    "net.peer.port",
    "net.host.name",
    "host.name",
    "container.name",
    "operation.name",
    "component",
    "span.kind",
    "error",
    "error.type",
    "error.message",
}


def _parse_timestamp(val: Any) -> datetime:
    """Parses various timestamp formats into UTC datetime."""
    if not val:
        return datetime.now(UTC)
    if isinstance(val, (int, float)):
        if val > 1e15:  # Nanoseconds
            return datetime.fromtimestamp(val / 1_000_000_000.0, tz=UTC)
        if val > 1e11:  # Milliseconds
            return datetime.fromtimestamp(val / 1000.0, tz=UTC)
        return datetime.fromtimestamp(val, tz=UTC)
    if isinstance(val, str):
        cleaned = val.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except Exception:
            return datetime.now(UTC)
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    return datetime.now(UTC)


class TraceNormalizer:
    """Standardizes heterogenous trace and span payloads into NormalizedSpanRecord instances."""

    @classmethod
    def sanitize_span_attributes(cls, attributes: dict[str, Any]) -> dict[str, Any]:
        """Enforces Group 7 privacy controls on span attributes."""
        if not attributes or not isinstance(attributes, dict):
            return {}

        sanitized_attrs: dict[str, Any] = {}
        for key, value in attributes.items():
            key_str = str(key)
            key_lower = key_str.lower()

            # 1. Drop or redact explicitly sensitive keys
            if any(s in key_lower for s in SENSITIVE_DICT_KEYS) or any(
                sensitive in key_lower
                for sensitive in ["auth", "cookie", "token", "key", "secret", "password", "credential"]
            ):
                sanitized_attrs[key_str] = "[REDACTED]"
                continue

            # 2. String values sanitized through Group 7 DataSanitizer
            if isinstance(value, str):
                sanitized_attrs[key_str] = DataSanitizer.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized_attrs[key_str] = DataSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized_attrs[key_str] = DataSanitizer.sanitize_list(value)
            else:
                sanitized_attrs[key_str] = value

        return sanitized_attrs

    @classmethod
    def normalize_span(
        cls,
        raw_span: dict[str, Any],
        default_source: str = "opentelemetry",
        default_env: str = "production",
    ) -> tuple[Optional[NormalizedSpanRecord], Optional[str]]:
        """Validates, sanitizes, and normalizes a single span dictionary."""
        # 1. Extract IDs
        trace_id = raw_span.get("trace_id") or raw_span.get("traceId")
        span_id = raw_span.get("span_id") or raw_span.get("spanId")
        parent_span_id = raw_span.get("parent_span_id") or raw_span.get("parentSpanId")

        if not trace_id or not isinstance(trace_id, str) or not trace_id.strip():
            return None, "Missing or invalid trace_id"
        if not span_id or not isinstance(span_id, str) or not span_id.strip():
            return None, "Missing or invalid span_id"

        trace_id = trace_id.strip().lower().replace("0x", "")
        span_id = span_id.strip().lower().replace("0x", "")
        if parent_span_id:
            parent_span_id = str(parent_span_id).strip().lower().replace("0x", "")
            if not parent_span_id or parent_span_id == "0000000000000000":
                parent_span_id = None

        # 2. Extract Timing
        start_ts = _parse_timestamp(
            raw_span.get("timestamp_start")
            or raw_span.get("startTimeUnixNano")
            or raw_span.get("startTime")
            or raw_span.get("start_time")
        )
        end_ts = _parse_timestamp(
            raw_span.get("timestamp_end")
            or raw_span.get("endTimeUnixNano")
            or raw_span.get("endTime")
            or raw_span.get("end_time")
        )

        # Handle duration & clock skew
        raw_duration = raw_span.get("duration_ms")
        if raw_duration is not None:
            duration_ms = float(raw_duration)
        else:
            duration_ms = (end_ts - start_ts).total_seconds() * 1000.0

        # Handle negative duration due to clock skew
        if duration_ms < 0:
            duration_ms = 0.1
            end_ts = start_ts + timedelta(milliseconds=0.1)

        # 3. Extract and normalize Service & Environment
        raw_service = (
            raw_span.get("service_name")
            or raw_span.get("service")
            or raw_span.get("attributes", {}).get("service.name")
            or "unknown-service"
        )
        service_name = ServiceIdentityNormalizer.normalize(raw_service)

        raw_env = (
            raw_span.get("environment")
            or raw_span.get("attributes", {}).get("deployment.environment")
            or default_env
        )
        environment = EnvironmentNormalizer.normalize(raw_env)

        # 4. Operation Name & Span Kind
        operation_name = (
            raw_span.get("operation_name")
            or raw_span.get("name")
            or raw_span.get("operation")
            or "operation"
        )
        span_kind = str(raw_span.get("span_kind") or raw_span.get("kind") or "SERVER").upper()

        # 5. Extract and sanitize attributes
        raw_attrs = raw_span.get("attributes") or raw_span.get("sanitized_attributes") or {}
        if not isinstance(raw_attrs, dict):
            raw_attrs = {}
        sanitized_attributes = cls.sanitize_span_attributes(raw_attrs)

        # 6. Status & Status Message
        status_val = raw_span.get("status")
        status_msg = raw_span.get("status_message") or raw_span.get("statusMessage")
        if isinstance(status_val, dict):
            status_code = status_val.get("code")
            status_msg = status_val.get("message") or status_msg
            if status_code in (2, "STATUS_CODE_ERROR", "ERROR"):
                status_str = "ERROR"
            elif status_code in (1, "STATUS_CODE_OK", "OK"):
                status_str = "OK"
            else:
                status_str = "UNSET"
        elif str(status_val).upper() in ("ERROR", "STATUS_CODE_ERROR", "FAIL", "FAILED"):
            status_str = "ERROR"
        elif str(status_val).upper() in ("OK", "STATUS_CODE_OK", "SUCCESS"):
            status_str = "OK"
        else:
            status_str = "OK"

        # 7. Extract Protocol Metadata (HTTP, RPC, DB)
        http_method = (
            raw_span.get("http_method")
            or sanitized_attributes.get("http.method")
            or sanitized_attributes.get("http.request.method")
        )
        http_route = (
            raw_span.get("http_route")
            or sanitized_attributes.get("http.route")
            or sanitized_attributes.get("http.target")
        )
        http_status_code = (
            raw_span.get("http_status_code")
            or sanitized_attributes.get("http.status_code")
            or sanitized_attributes.get("http.response.status_code")
        )
        if http_status_code is not None:
            try:
                http_status_code = int(http_status_code)
                if http_status_code >= 500:
                    status_str = "ERROR"
            except (ValueError, TypeError):
                http_status_code = None

        rpc_system = raw_span.get("rpc_system") or sanitized_attributes.get("rpc.system")
        rpc_service = raw_span.get("rpc_service") or sanitized_attributes.get("rpc.service")
        rpc_method = raw_span.get("rpc_method") or sanitized_attributes.get("rpc.method")
        database_system = raw_span.get("database_system") or sanitized_attributes.get("db.system")
        database_operation = raw_span.get("database_operation") or sanitized_attributes.get("db.operation")
        peer_service = (
            raw_span.get("peer_service")
            or sanitized_attributes.get("peer.service")
            or sanitized_attributes.get("net.peer.name")
        )
        host = raw_span.get("host") or sanitized_attributes.get("host.name")
        service_version = (
            raw_span.get("service_version")
            or sanitized_attributes.get("service.version")
        )

        record = NormalizedSpanRecord(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            timestamp_start=start_ts,
            timestamp_end=end_ts,
            duration_ms=round(duration_ms, 2),
            service_name=service_name,
            service_version=service_version,
            environment=environment,
            operation_name=operation_name,
            span_kind=span_kind,
            status=status_str,
            status_message=status_msg,
            http_method=str(http_method).upper() if http_method else None,
            http_route=str(http_route) if http_route else None,
            http_status_code=http_status_code,
            rpc_system=str(rpc_system) if rpc_system else None,
            rpc_service=str(rpc_service) if rpc_service else None,
            rpc_method=str(rpc_method) if rpc_method else None,
            database_system=str(database_system) if database_system else None,
            database_operation=str(database_operation) if database_operation else None,
            peer_service=str(peer_service) if peer_service else None,
            host=str(host) if host else None,
            source=raw_span.get("source") or default_source,
            schema_version="1.0",
            sanitized_attributes=sanitized_attributes,
        )

        return record, None
