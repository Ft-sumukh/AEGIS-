"""
Prometheus Observability Adapter.
Normalizes Prometheus vector and matrix query payloads into Aegis TelemetryRecords.
Provides a resilient pull-based scraper with circuit breaking and timeout bounds.
"""

from datetime import UTC, datetime
from typing import Any, Optional
import httpx

from app.core.logging import get_logger
from app.telemetry.abstractions import TelemetryAdapter, TelemetrySource
from app.telemetry.normalizer import EnvironmentNormalizer, MetricNameNormalizer, ServiceIdentityNormalizer
from app.telemetry.schemas import (
    SourceHealthStatus,
    SourceStatus,
    TelemetryEventType,
    TelemetryRecord,
    TelemetrySourceType,
)

logger = get_logger("aegis.telemetry.adapters.prometheus")


class PrometheusAdapter(TelemetryAdapter):
    """Normalizes Prometheus standard API query responses (vector & matrix formats)."""

    def validate(self, raw_data: Any) -> tuple[bool, list[str]]:
        """Validates Prometheus JSON query structure."""
        errors: list[str] = []
        if not isinstance(raw_data, dict):
            return False, ["Payload must be a JSON object"]

        # Support standard Prometheus API response format
        status_field = raw_data.get("status")
        if status_field != "success":
            errors.append(f"Prometheus query status is '{status_field}', expected 'success'")

        data = raw_data.get("data")
        if not isinstance(data, dict):
            errors.append("Prometheus payload missing 'data' object")
            return False, errors

        result = data.get("result")
        if not isinstance(result, list):
            errors.append("Prometheus data.result must be a list")

        return len(errors) == 0, errors

    def normalize(self, raw_data: Any) -> list[TelemetryRecord]:
        """Converts Prometheus result objects into normalized TelemetryRecords."""
        records: list[TelemetryRecord] = []
        data = raw_data.get("data", {})
        result_type = data.get("resultType", "vector")
        results = data.get("result", [])

        for item in results:
            metric_labels = item.get("metric", {})
            raw_metric_name = metric_labels.get("__name__", "prometheus_metric")

            # Resolve service identity from common labels
            raw_service = (
                metric_labels.get("service")
                or metric_labels.get("app")
                or metric_labels.get("job")
                or "unknown-service"
            )
            canonical_service = ServiceIdentityNormalizer.normalize(raw_service)

            # Resolve environment
            raw_env = (
                metric_labels.get("environment")
                or metric_labels.get("env")
                or metric_labels.get("namespace")
                or "production"
            )
            canonical_env = EnvironmentNormalizer.normalize(raw_env)

            # Canonical metric name
            normalized_metric = MetricNameNormalizer.normalize(raw_metric_name, dimensions=metric_labels)

            # Derive unit
            unit = "count"
            if "duration" in raw_metric_name or "latency" in raw_metric_name or "seconds" in raw_metric_name:
                unit = "seconds"
            elif "bytes" in raw_metric_name:
                unit = "bytes"
            elif "ratio" in raw_metric_name or "percentage" in raw_metric_name or "rate" in raw_metric_name:
                unit = "ratio"

            host = metric_labels.get("instance") or metric_labels.get("node")

            # Handle vector (single timestamp/value) vs matrix (multiple timestamp/value pairs)
            values_to_process: list[tuple[float, str]] = []
            if result_type == "vector" and "value" in item:
                val = item["value"]
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    values_to_process.append((float(val[0]), str(val[1])))
            elif result_type == "matrix" and "values" in item:
                for pair in item["values"]:
                    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                        values_to_process.append((float(pair[0]), str(pair[1])))

            for epoch_ts, str_val in values_to_process:
                try:
                    num_val = float(str_val)
                except (ValueError, TypeError):
                    continue

                ts = datetime.fromtimestamp(epoch_ts, tz=UTC)
                record = TelemetryRecord(
                    source="prometheus",
                    source_type=TelemetrySourceType.PROMETHEUS,
                    event_type=TelemetryEventType.METRIC,
                    timestamp=ts,
                    service=canonical_service,
                    environment=canonical_env,
                    host=host,
                    metric_name=normalized_metric,
                    value=num_val,
                    unit=unit,
                    dimensions=metric_labels,
                    severity="INFO" if not normalized_metric.endswith("error_rate") or num_val < 0.05 else "WARN",
                    metadata={"raw_metric_name": raw_metric_name, "prom_job": metric_labels.get("job")},
                    schema_version="1.0",
                )
                records.append(record)

        return records


class PrometheusSource(TelemetrySource):
    """Pull-based Prometheus telemetry source with circuit breaker."""

    def __init__(
        self,
        endpoint_url: str = "http://localhost:9090",
        name: str = "prometheus",
        timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__(name=name, source_type=TelemetrySourceType.PROMETHEUS)
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.adapter = PrometheusAdapter()
        self.last_status: SourceStatus = SourceStatus.HEALTHY
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.records_received = 0
        self.records_rejected = 0
        self.last_error: Optional[str] = None
        self.last_latency_ms: Optional[float] = None

    def query(self, promql_query: str) -> list[TelemetryRecord]:
        """Executes a PromQL instant query wrapped in circuit breaker protection."""
        url = f"{self.endpoint_url}/api/v1/query"

        def _do_query() -> list[TelemetryRecord]:
            start_time = datetime.now(UTC)
            try:
                resp = httpx.get(
                    url,
                    params={"query": promql_query},
                    timeout=self.timeout_seconds,
                )
                latency = (datetime.now(UTC) - start_time).total_seconds() * 1000.0
                self.last_latency_ms = round(latency, 2)

                if resp.status_code != 200:
                    raise RuntimeError(f"Prometheus HTTP {resp.status_code}: {resp.text[:200]}")

                payload = resp.json()
                valid, errors = self.adapter.validate(payload)
                if not valid:
                    self.records_rejected += 1
                    raise ValueError(f"Malformed Prometheus response: {', '.join(errors)}")

                records = self.adapter.normalize(payload)
                self.records_received += len(records)
                self.last_success = datetime.now(UTC)
                self.last_status = SourceStatus.HEALTHY
                self.last_error = None
                return records

            except Exception as exc:
                self.last_failure = datetime.now(UTC)
                self.last_status = SourceStatus.DEGRADED
                self.last_error = str(exc)
                logger.warning(f"Prometheus query failed: {exc}")
                raise

        return self.circuit_breaker.execute(_do_query)

    def fetch(self, since: Optional[datetime] = None) -> list[TelemetryRecord]:
        """Pulls standard baseline operational metrics from Prometheus."""
        # Core query set covering CPU, memory, errors, and latency
        queries = [
            'http_requests_total{status=~"5.."}',
            'http_request_duration_seconds',
            'node_cpu_utilization_ratio',
            'node_memory_utilization_ratio',
        ]
        all_records: list[TelemetryRecord] = []
        for q in queries:
            try:
                records = self.query(q)
                all_records.extend(records)
            except Exception as e:
                logger.debug(f"Prometheus query '{q}' did not return records: {e}")
        return all_records

    def check_health(self) -> SourceHealthStatus:
        """Pings Prometheus /-/healthy endpoint."""
        url = f"{self.endpoint_url}/-/healthy"
        try:
            resp = httpx.get(url, timeout=3.0)
            if resp.status_code == 200:
                self.last_status = SourceStatus.HEALTHY
                self.last_error = None
            else:
                self.last_status = SourceStatus.DEGRADED
                self.last_error = f"Prometheus returned HTTP {resp.status_code}"
        except Exception as e:
            self.last_status = SourceStatus.FAILED
            self.last_error = str(e)

        return SourceHealthStatus(
            source=self.name,
            source_type=self.source_type,
            status=self.last_status,
            last_success=self.last_success,
            last_failure=self.last_failure,
            records_received=self.records_received,
            records_rejected=self.records_rejected,
            latency_ms=self.last_latency_ms,
            error_message=self.last_error,
        )
