"""
Canonical normalization for service identities, metric names, and environments.
Prevents vendor-specific naming conventions from leaking into the analytics layer.
"""

import re
from typing import Any, Optional


class ServiceIdentityNormalizer:
    """Normalizes heterogenous service names into unified canonical identifiers."""

    # Explicit alias map for distributed infrastructure
    KNOWN_ALIASES: dict[str, str] = {
        "checkout-api": "checkout-service",
        "checkout_service": "checkout-service",
        "checkoutservice": "checkout-service",
        "prod-checkout": "checkout-service",
        "checkout": "checkout-service",

        "catalog-api": "catalog-service",
        "catalog_service": "catalog-service",
        "catalog": "catalog-service",

        "payment-api": "payment-gateway",
        "payment_service": "payment-gateway",
        "payments": "payment-gateway",
        "payment_gateway": "payment-gateway",

        "auth-api": "auth-service",
        "auth_service": "auth-service",
        "auth": "auth-service",
        "authentication": "auth-service",

        "api-gateway": "api-gateway",
        "api_gateway": "api-gateway",
        "gateway": "api-gateway",
        "edge-gateway": "api-gateway",

        "billing-service": "billing-service",
        "billing_service": "billing-service",
        "billing": "billing-service",

        "notification-service": "notification-service",
        "notification_service": "notification-service",
    }

    @classmethod
    def normalize(cls, raw_service: str) -> str:
        """Transforms arbitrary service identity string into canonical slug."""
        if not raw_service:
            return "unknown-service"

        cleaned = raw_service.strip().lower()
        if cleaned in cls.KNOWN_ALIASES:
            return cls.KNOWN_ALIASES[cleaned]

        # General normalization: replace underscores and dots with hyphens
        normalized = re.sub(r"[._\s]+", "-", cleaned)
        normalized = re.sub(r"[^a-z0-9\-]", "", normalized)
        return normalized or "unknown-service"


class MetricNameNormalizer:
    """Normalizes external observability metric names into Aegis standard operational metrics."""

    METRIC_MAP: dict[str, str] = {
        # Prometheus standard exporter metrics
        "http_request_duration_seconds": "api_latency",
        "http_request_duration_ms": "api_latency",
        "http_latency_seconds": "api_latency",
        "request_duration_seconds": "api_latency",

        "http_requests_total_5xx": "api_error_rate",
        "http_5xx_rate": "api_error_rate",
        "http_errors_total": "api_error_rate",
        "api_errors": "api_error_rate",

        "node_cpu_utilization_ratio": "cpu_utilization",
        "container_cpu_usage_seconds_total": "cpu_utilization",
        "system_cpu_usage": "cpu_utilization",
        "cpu_usage": "cpu_utilization",

        "node_memory_utilization_ratio": "memory_utilization",
        "container_memory_working_set_bytes": "memory_utilization",
        "system_memory_usage": "memory_utilization",
        "memory_usage": "memory_utilization",

        "checkout_failures_total": "checkout_failure_rate",
        "checkout_errors": "checkout_failure_rate",
        "order_failures": "order_failure_rate",

        "pg_stat_activity_count": "db_connection_pool_usage",
        "database_connections_active": "db_connection_pool_usage",
    }

    @classmethod
    def normalize(cls, raw_metric: str, dimensions: Optional[dict[str, Any]] = None) -> str:
        """Maps vendor metric name to Aegis standard name with optional dimension context."""
        if not raw_metric:
            return "custom_metric"

        cleaned = raw_metric.strip().lower()

        # Handle Prometheus http_requests_total with status=5xx label
        if cleaned == "http_requests_total" and dimensions:
            status_code = str(dimensions.get("status", dimensions.get("status_code", "")))
            if status_code.startswith("5"):
                return "api_error_rate"
            elif status_code.startswith("2"):
                return "api_request_rate"

        if cleaned in cls.METRIC_MAP:
            return cls.METRIC_MAP[cleaned]

        # Strip vendor namespaces (e.g. aws.ec2.cpu -> cpu, prom_node_cpu -> node_cpu)
        parts = cleaned.split(".")
        if len(parts) > 1:
            candidate = parts[-1]
            if candidate in cls.METRIC_MAP:
                return cls.METRIC_MAP[candidate]

        return cleaned


class EnvironmentNormalizer:
    """Normalizes runtime environment strings."""

    ENV_MAP = {
        "prod": "production",
        "production": "production",
        "prd": "production",
        "stage": "staging",
        "staging": "staging",
        "stg": "staging",
        "dev": "development",
        "development": "development",
        "local": "development",
        "test": "development",
        "demo": "demo",
        "synthetic": "demo",
    }

    @classmethod
    def normalize(cls, raw_env: Optional[str]) -> str:
        if not raw_env:
            return "production"
        cleaned = raw_env.strip().lower()
        return cls.ENV_MAP.get(cleaned, "production")
