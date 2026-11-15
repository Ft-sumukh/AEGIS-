"""SRE Runbook and Automated Playbook Catalog Service."""

import logging
from typing import Any

from app.models.incident import Incident

logger = logging.getLogger("aegis.runbooks")

RUNBOOK_CATALOG: list[dict[str, Any]] = [
    {
        "id": "RB-PAYMENT-01",
        "title": "Payment Gateway Throttling & Degraded Checkout",
        "category": "PAYMENT_FAILURE",
        "severity": "CRITICAL",
        "target_services": ["payment-service", "checkout-service"],
        "summary": "Standard operating procedure for responding to checkout failure spikes and third-party payment gateway latency.",
        "prerequisites": [
            "Verify network egress connectivity to payment acquirer.",
            "Confirm whether a recent deployment or configuration change was released within the last 4 hours.",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Inspect API Gateway logs for downstream HTTP 429 vs 504 status codes.", "verified": False},
            {"step": 2, "action": "Check PostgreSQL connection pool saturation on transaction-db.", "verified": False},
            {"step": 3, "action": "Review distributed trace waterfall for critical-path bottlenecks.", "verified": False},
        ],
        "recommended_actions": [
            {
                "action_type": "ENABLE_FEATURE_FLAG",
                "title": "Enable Circuit Breaker Fallback Gateway",
                "risk_level": "LOW",
                "parameters": {"flag_name": "circuit_breaker_payment_v2", "enabled": True},
            },
            {
                "action_type": "ROLLBACK_DEPLOYMENT",
                "title": "Rollback Recent Payment Service Deployment",
                "risk_level": "HIGH",
                "parameters": {"service_name": "payment-service", "target_deployment_id": "dep-payment-v2.3.9"},
            },
        ],
        "verification_criteria": [
            "Checkout error rate returns to < 0.5% for 5 continuous evaluation minutes.",
            "Payment P99 latency returns to baseline (< 200ms).",
        ],
    },
    {
        "id": "RB-DATABASE-02",
        "title": "Database Connection Pool Starvation & Latency Surge",
        "category": "DATABASE",
        "severity": "HIGH",
        "target_services": ["postgres-cluster", "order-service"],
        "summary": "Mitigation steps for connection pool exhaustion and query queue build-up.",
        "prerequisites": [
            "Check replica lag across PostgreSQL read replicas.",
            "Verify free disk space and IOPS utilization on RDS/database nodes.",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Check active client connections vs max_connections threshold.", "verified": False},
            {"step": 2, "action": "Inspect query locks and blocked PIDs.", "verified": False},
            {"step": 3, "action": "Analyze slow query log for missing index scans.", "verified": False},
        ],
        "recommended_actions": [
            {
                "action_type": "RESTART_SERVICE",
                "title": "Gracefully Restart Connection Pooler",
                "risk_level": "MEDIUM",
                "parameters": {"service_name": "order-service", "graceful_timeout_sec": 30},
            },
            {
                "action_type": "CLEAR_CACHE",
                "title": "Flush Stale Query Result Cache",
                "risk_level": "LOW",
                "parameters": {"cache_name": "redis-order-cache", "pattern": "order:*"},
            },
        ],
        "verification_criteria": [
            "Active database connection count drops below 40% pool capacity.",
            "Transaction commit latency normalizes under 25ms.",
        ],
    },
    {
        "id": "RB-AUTH-03",
        "title": "Identity Provider & Token Authentication Failure Mitigation",
        "category": "AUTHENTICATION",
        "severity": "HIGH",
        "target_services": ["auth-service", "identity-provider"],
        "summary": "Playbook for elevated 401/500 authentication errors and JWT certificate synchronization.",
        "prerequisites": [
            "Verify token signing certificate expiration and JWKS key rotation status.",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Inspect Redis session store latency and memory consumption.", "verified": False},
            {"step": 2, "action": "Check token validation error codes (expired vs invalid signature).", "verified": False},
        ],
        "recommended_actions": [
            {
                "action_type": "ROLLBACK_DEPLOYMENT",
                "title": "Rollback Auth Service to Stable Build",
                "risk_level": "HIGH",
                "parameters": {"service_name": "auth-service", "target_deployment_id": "dep-auth-stable"},
            },
            {
                "action_type": "SCALE_SERVICE",
                "title": "Scale Auth Service Instances for Surge",
                "risk_level": "MEDIUM",
                "parameters": {"service_name": "auth-service", "target_replicas": 6},
            },
        ],
        "verification_criteria": [
            "Authentication success rate exceeds 99.8%.",
            "Token verification latency is under 45ms.",
        ],
    },
    {
        "id": "RB-TRAFFIC-04",
        "title": "Ingress Surge & Horizontal Autoscaling Playbook",
        "category": "INFRASTRUCTURE",
        "severity": "MEDIUM",
        "target_services": ["ingress-router", "api-gateway"],
        "summary": "Procedure for managing unexpected traffic spikes and edge routing bottlenecks.",
        "prerequisites": [
            "Verify edge CDN cache hit ratio.",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Inspect ingress requests per second by geographic region.", "verified": False},
            {"step": 2, "action": "Check edge firewall and rate-limiting triggers.", "verified": False},
        ],
        "recommended_actions": [
            {
                "action_type": "SCALE_SERVICE",
                "title": "Scale Ingress Routers and API Gateway",
                "risk_level": "MEDIUM",
                "parameters": {"service_name": "api-gateway", "target_replicas": 12},
            },
        ],
        "verification_criteria": [
            "Ingress queue depth drops to 0.",
            "HTTP 429 rate stabilizes below 0.1%.",
        ],
    },
]


class RunbookService:
    """Provides querying and matching of SRE playbooks against active incidents."""

    @classmethod
    def list_runbooks(cls) -> list[dict[str, Any]]:
        return RUNBOOK_CATALOG

    @classmethod
    def get_runbook(cls, runbook_id: str) -> dict[str, Any] | None:
        for rb in RUNBOOK_CATALOG:
            if rb["id"] == runbook_id.upper():
                return rb
        return None

    @classmethod
    def match_for_incident(cls, incident: Incident) -> list[dict[str, Any]]:
        """Matches relevant runbooks based on incident category and affected services."""
        category = (incident.category or "").upper()
        affected = set(incident.affected_systems or [])

        matches = []
        for rb in RUNBOOK_CATALOG:
            score = 0
            # Category match
            if rb["category"] in category or category in rb["category"]:
                score += 3
            # Service match
            common_services = affected.intersection(set(rb["target_services"]))
            if common_services:
                score += len(common_services) * 2

            if score > 0:
                matches.append({"score": score, "runbook": rb})

        # Sort by match score descending
        matches.sort(key=lambda m: m["score"], reverse=True)
        return [m["runbook"] for m in matches] or [RUNBOOK_CATALOG[0]]
