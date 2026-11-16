"""AI Tool Registry initialization and schemas."""

from typing import Any

from app.agents.tools import operational
from app.agents.tools.registry import ALLOWED_TOOLS, ToolRegistry


def get_default_tool_registry() -> ToolRegistry:
    """Instantiates and registers all allowlisted operational tools."""
    registry = ToolRegistry()

    # 1. get_incident
    registry.register(
        name="get_incident",
        func=operational.get_incident,
        schema={
            "name": "get_incident",
            "description": "Retrieves high-level metadata for an operational incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident to inspect",
                    }
                },
                "required": ["incident_id"],
            },
        },
    )

    # 2. get_timeline
    registry.register(
        name="get_timeline",
        func=operational.get_timeline,
        schema={
            "name": "get_timeline",
            "description": "Retrieves chronological ordered timeline events surrounding the incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident",
                    }
                },
                "required": ["incident_id"],
            },
        },
    )

    # 3. get_anomalies
    registry.register(
        name="get_anomalies",
        func=operational.get_anomalies,
        schema={
            "name": "get_anomalies",
            "description": "Retrieves statistical metric anomalies correlated with the incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident",
                    }
                },
                "required": ["incident_id"],
            },
        },
    )

    # 4. get_metric_window
    registry.register(
        name="get_metric_window",
        func=operational.get_metric_window,
        schema={
            "name": "get_metric_window",
            "description": "Queries time-series telemetry data for a specific metric within a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "description": "Metric name to inspect"},
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                    "service_name": {
                        "type": "string",
                        "description": "Optional service name filter",
                    },
                },
                "required": ["metric_name", "start_time", "end_time"],
            },
        },
    )

    # 5. compare_metrics
    registry.register(
        name="compare_metrics",
        func=operational.compare_metrics,
        schema={
            "name": "compare_metrics",
            "description": "Compares metric statistics between a baseline window and the incident window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "description": "Target metric name"},
                    "baseline_start": {"type": "string", "description": "Baseline start timestamp"},
                    "baseline_end": {"type": "string", "description": "Baseline end timestamp"},
                    "incident_start": {"type": "string", "description": "Incident start timestamp"},
                    "incident_end": {"type": "string", "description": "Incident end timestamp"},
                    "service_name": {"type": "string", "description": "Optional service filter"},
                },
                "required": [
                    "metric_name",
                    "baseline_start",
                    "baseline_end",
                    "incident_start",
                    "incident_end",
                ],
            },
        },
    )

    # 6. get_deployments
    registry.register(
        name="get_deployments",
        func=operational.get_deployments,
        schema={
            "name": "get_deployments",
            "description": "Retrieves software deployment events within a time window (secrets and credentials stripped).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                    "service_name": {"type": "string", "description": "Optional service filter"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    )

    # 7. get_system_events
    registry.register(
        name="get_system_events",
        func=operational.get_system_events,
        schema={
            "name": "get_system_events",
            "description": "Retrieves system operational events (restarts, errors, alerts) within a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                    "service_name": {"type": "string", "description": "Optional service filter"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    )

    # 8. get_support_tickets
    registry.register(
        name="get_support_tickets",
        func=operational.get_support_tickets,
        schema={
            "name": "get_support_tickets",
            "description": "Retrieves customer support tickets with customer identity pseudonymized and PII stripped.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                    "category": {"type": "string", "description": "Optional ticket category"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    )

    # 9. get_customer_complaints
    registry.register(
        name="get_customer_complaints",
        func=operational.get_customer_complaints,
        schema={
            "name": "get_customer_complaints",
            "description": "Retrieves customer complaints with customer IDs pseudonymized.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    )

    # 10. get_impact
    registry.register(
        name="get_impact",
        func=operational.get_impact,
        schema={
            "name": "get_impact",
            "description": "Retrieves business blast radius and customer impact metrics for an incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident",
                    }
                },
                "required": ["incident_id"],
            },
        },
    )

    # 11. get_related_incidents
    registry.register(
        name="get_related_incidents",
        func=operational.get_related_incidents,
        schema={
            "name": "get_related_incidents",
            "description": "Retrieves historical incidents in the same category or affecting similar systems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "UUID of the incident",
                    }
                },
                "required": ["incident_id"],
            },
        },
    )

    # 12. get_trace
    registry.register(
        name="get_trace",
        func=operational.get_trace,
        schema={
            "name": "get_trace",
            "description": "Retrieves full reconstructed distributed trace tree with sanitized attributes and timings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "W3C Trace ID string"}
                },
                "required": ["trace_id"],
            },
        },
    )

    # 13. get_trace_summary
    registry.register(
        name="get_trace_summary",
        func=operational.get_trace_summary,
        schema={
            "name": "get_trace_summary",
            "description": "Retrieves compact executive summary of a trace without full span payload.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "W3C Trace ID string"}
                },
                "required": ["trace_id"],
            },
        },
    )

    # 14. get_slow_traces
    registry.register(
        name="get_slow_traces",
        func=operational.get_slow_traces,
        schema={
            "name": "get_slow_traces",
            "description": "Queries slowest distributed traces within a time window for latency investigation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Optional service name filter"},
                    "limit": {"type": "integer", "description": "Max traces to return (default 10)"},
                    "min_duration_ms": {"type": "number", "description": "Minimum latency threshold in ms"},
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                },
            },
        },
    )

    # 15. get_failed_traces
    registry.register(
        name="get_failed_traces",
        func=operational.get_failed_traces,
        schema={
            "name": "get_failed_traces",
            "description": "Queries distributed traces containing HTTP 5xx errors or failed spans.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Optional service name filter"},
                    "limit": {"type": "integer", "description": "Max traces to return (default 10)"},
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                },
            },
        },
    )

    # 16. get_service_dependencies
    registry.register(
        name="get_service_dependencies",
        func=operational.get_service_dependencies,
        schema={
            "name": "get_service_dependencies",
            "description": "Discovers directed service dependencies, call rates, error rates, and p95 latencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Optional filter for a specific service"},
                    "environment": {"type": "string", "description": "Environment filter (default production)"},
                    "time_window_hours": {"type": "integer", "description": "Time window in hours (default 24)"},
                },
            },
        },
    )

    # 17. get_service_trace_health
    registry.register(
        name="get_service_trace_health",
        func=operational.get_service_trace_health,
        schema={
            "name": "get_service_trace_health",
            "description": "Calculates health metrics (error rate, p95, slow request %, dependency failures) for a service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Target service name"},
                    "environment": {"type": "string", "description": "Environment filter (default production)"},
                    "time_window_hours": {"type": "integer", "description": "Time window in hours (default 6)"},
                },
                "required": ["service_name"],
            },
        },
    )

    # 18. get_critical_path
    registry.register(
        name="get_critical_path",
        func=operational.get_critical_path,
        schema={
            "name": "get_critical_path",
            "description": "Calculates critical path segments determining trace latency and service self-time contributions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "W3C Trace ID string"}
                },
                "required": ["trace_id"],
            },
        },
    )

    # 19. get_trace_error_patterns
    registry.register(
        name="get_trace_error_patterns",
        func=operational.get_trace_error_patterns,
        schema={
            "name": "get_trace_error_patterns",
            "description": "Extracts downstream error origination and propagation chains across call graphs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Optional service filter"},
                    "start_time": {"type": "string", "description": "ISO-8601 start timestamp"},
                    "end_time": {"type": "string", "description": "ISO-8601 end timestamp"},
                },
            },
        },
    )

    # 20. get_correlated_trace_evidence
    registry.register(
        name="get_correlated_trace_evidence",
        func=operational.get_correlated_trace_evidence,
        schema={
            "name": "get_correlated_trace_evidence",
            "description": "Synthesizes multi-source cross-correlation linking deployments, traces, metrics, logs, and business impact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "UUID of the incident"}
                },
                "required": ["incident_id"],
            },
        },
    )

    return registry
