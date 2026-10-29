"""Unit tests for TraceNormalizer standardizing distributed trace spans."""

from datetime import UTC, datetime, timedelta

from app.telemetry.trace_normalizer import TraceNormalizer


def test_normalize_valid_span() -> None:
    """Verify standard span normalization with full protocol metadata."""
    now = datetime.now(UTC)
    raw = {
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "parent_span_id": "5fb397be34d23b0f",
        "timestamp_start": now.isoformat(),
        "timestamp_end": (now + timedelta(milliseconds=150)).isoformat(),
        "service": "cart-service",
        "environment": "production",
        "operation_name": "POST /api/v1/cart",
        "span_kind": "SERVER",
        "http_method": "POST",
        "http_route": "/api/v1/cart",
        "http_status_code": 200,
        "attributes": {
            "http.method": "POST",
            "db.system": "postgresql",
            "net.peer.name": "payment-service",
        },
    }

    record, err = TraceNormalizer.normalize_span(raw)
    assert err is None
    assert record is not None
    assert record.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert record.span_id == "00f067aa0ba902b7"
    assert record.parent_span_id == "5fb397be34d23b0f"
    assert record.duration_ms == 150.0
    assert record.service_name == "cart-service"
    assert record.environment == "production"
    assert record.status == "OK"
    assert record.http_method == "POST"
    assert record.peer_service == "payment-service"


def test_service_and_environment_normalization() -> None:
    """Verify service alias and environment normalization."""
    raw = {
        "traceId": "0xABCDEF0123456789ABCDEF0123456789",
        "spanId": "0x1234567890ABCDEF",
        "startTime": 1700000000000,
        "endTime": 1700000000500,
        "service": "checkout_service",
        "environment": "prod",
        "operation": "checkout",
    }

    record, err = TraceNormalizer.normalize_span(raw)
    assert err is None
    assert record is not None
    assert record.trace_id == "abcdef0123456789abcdef0123456789"
    assert record.span_id == "1234567890abcdef"
    assert record.service_name == "checkout-service"
    assert record.environment == "production"
    assert record.duration_ms == 500.0


def test_clock_skew_correction() -> None:
    """Verify clock skew (end time before start time) is corrected without negative durations."""
    now = datetime.now(UTC)
    raw = {
        "trace_id": "11223344556677881122334455667788",
        "span_id": "1122334455667788",
        "timestamp_start": (now + timedelta(milliseconds=100)).isoformat(),
        "timestamp_end": now.isoformat(),  # End before start
        "service": "order-service",
    }

    record, err = TraceNormalizer.normalize_span(raw)
    assert err is None
    assert record is not None
    assert record.duration_ms >= 0.1
    assert record.timestamp_end >= record.timestamp_start


def test_status_mapping_and_http_error() -> None:
    """Verify OTLP status object and HTTP 5xx error inference."""
    raw_otlp_err = {
        "trace_id": "aabbccddeeff00112233445566778899",
        "span_id": "aabbccddeeff0011",
        "service": "payment-service",
        "status": {"code": 2, "message": "Upstream timeout"},
    }
    rec1, err1 = TraceNormalizer.normalize_span(raw_otlp_err)
    assert err1 is None
    assert rec1 is not None
    assert rec1.status == "ERROR"
    assert rec1.status_message == "Upstream timeout"

    raw_http_err = {
        "trace_id": "aabbccddeeff00112233445566778899",
        "span_id": "aabbccddeeff0022",
        "service": "api-gateway",
        "http_status_code": 503,
    }
    rec2, err2 = TraceNormalizer.normalize_span(raw_http_err)
    assert err2 is None
    assert rec2 is not None
    assert rec2.status == "ERROR"


def test_missing_ids_rejection() -> None:
    """Verify invalid or missing trace_id / span_id are rejected."""
    raw_no_trace = {"span_id": "123", "service": "srv"}
    rec, err = TraceNormalizer.normalize_span(raw_no_trace)
    assert rec is None
    assert "trace_id" in str(err).lower()

    raw_no_span = {"trace_id": "abc", "service": "srv"}
    rec, err = TraceNormalizer.normalize_span(raw_no_span)
    assert rec is None
    assert "span_id" in str(err).lower()
