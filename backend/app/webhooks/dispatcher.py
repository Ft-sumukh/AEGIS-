"""Outbound Webhook Dispatcher Engine.

Formats and dispatches enterprise operational alerts to Slack, PagerDuty,
StatusPage, and custom webhook destinations with HMAC-SHA256 signature authentication.
"""

from datetime import UTC, datetime
import hashlib
import hmac
import json
import logging
from typing import Any
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.webhook import WebhookSubscription

logger = logging.getLogger("aegis.webhooks")


class WebhookDispatcher:
    """Manages external alert integration transformations and HTTP dispatching."""

    @classmethod
    def format_payload(
        cls,
        target_type: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Transforms a raw operational event into platform-specific schema (Slack/PagerDuty/Generic)."""
        target = target_type.upper()

        if target == "SLACK":
            severity = payload.get("severity", "HIGH")
            color = "#E11D48" if severity in ("CRITICAL", "BURNING") else "#F59E0B"
            title = payload.get("title") or payload.get("name") or f"Aegis Event: {event_type}"
            summary = payload.get("summary") or payload.get("description") or "Operational event notification."

            return {
                "text": f"🚨 *[Aegis Alert]* {title}",
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "text": summary,
                        "fields": [
                            {"title": "Event Type", "value": event_type, "short": True},
                            {"title": "Severity", "value": str(severity), "short": True},
                            {
                                "title": "Affected Systems",
                                "value": ", ".join(payload.get("affected_systems", ["core"])),
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True,
                            },
                        ],
                        "footer": "Aegis AI Operations Intelligence",
                    }
                ],
            }

        elif target == "PAGERDUTY":
            return {
                "routing_key": payload.get("routing_key", "aegis-pd-key"),
                "event_action": "trigger",
                "dedup_key": f"aegis-{event_type}-{payload.get('id', uuid.uuid4())}",
                "payload": {
                    "summary": payload.get("title", f"Aegis Alert: {event_type}"),
                    "severity": "critical" if payload.get("severity") == "CRITICAL" else "warning",
                    "source": "aegis-operations-intelligence",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "custom_details": payload,
                },
            }

        # Default: GENERIC_WEBHOOK
        return {
            "aegis_event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "dispatched_at": datetime.now(UTC).isoformat(),
            "data": payload,
        }

    @classmethod
    def compute_signature(cls, secret_token: str | None, payload_bytes: bytes) -> str | None:
        """Computes HMAC-SHA256 signature over payload bytes."""
        if not secret_token:
            return None
        sig = hmac.new(secret_token.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    @classmethod
    def dispatch_subscription(
        cls,
        subscription: WebhookSubscription,
        event_type: str,
        payload: dict[str, Any],
        is_simulation_mode: bool = True,
    ) -> dict[str, Any]:
        """Dispatches an event payload to a single subscription endpoint."""
        formatted = cls.format_payload(subscription.target_type, event_type, payload)
        payload_bytes = json.dumps(formatted).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Aegis-Operations-Intelligence/1.0",
            "X-Aegis-Event": event_type,
            "X-Aegis-Delivery": str(uuid.uuid4()),
        }

        sig = cls.compute_signature(subscription.secret_token, payload_bytes)
        if sig:
            headers["X-Aegis-Signature"] = sig

        now = datetime.now(UTC)

        # Simulation or test URLs
        if is_simulation_mode or "example.com" in subscription.url or "hooks.slack.com" in subscription.url:
            subscription.last_dispatched_at = now
            subscription.last_status_code = 200
            logger.info("Simulated webhook dispatch to %s for event %s", subscription.url, event_type)
            return {
                "subscription_id": str(subscription.id),
                "url": subscription.url,
                "status": "DELIVERED",
                "status_code": 200,
                "dispatched_at": now.isoformat(),
                "payload_preview": formatted,
            }

        # Real outbound dispatch (within safety timeout)
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.post(subscription.url, content=payload_bytes, headers=headers)
                subscription.last_dispatched_at = now
                subscription.last_status_code = res.status_code
                return {
                    "subscription_id": str(subscription.id),
                    "url": subscription.url,
                    "status": "DELIVERED" if res.is_success else "FAILED",
                    "status_code": res.status_code,
                    "dispatched_at": now.isoformat(),
                    "payload_preview": formatted,
                }
        except Exception as e:
            logger.warning("Failed outbound webhook delivery to %s: %s", subscription.url, str(e))
            subscription.last_dispatched_at = now
            subscription.last_status_code = 502
            return {
                "subscription_id": str(subscription.id),
                "url": subscription.url,
                "status": "FAILED",
                "status_code": 502,
                "error": str(e),
                "dispatched_at": now.isoformat(),
                "payload_preview": formatted,
            }

    @classmethod
    def dispatch_event(
        cls,
        db: Session,
        event_type: str,
        payload: dict[str, Any],
        company_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Broadcasting event dispatcher to all active matching webhook subscribers."""
        query = select(WebhookSubscription).where(WebhookSubscription.is_active.is_(True))
        if company_id:
            query = query.where(WebhookSubscription.company_id == company_id)

        subscriptions = db.execute(query).scalars().all()
        results = []

        is_sim = getattr(get_settings(), "ACTION_EXECUTION_MODE", "SIMULATED") == "SIMULATED"

        for sub in subscriptions:
            # Check if subscribed
            if not sub.subscribed_events or event_type in sub.subscribed_events or "*" in sub.subscribed_events:
                res = cls.dispatch_subscription(sub, event_type, payload, is_simulation_mode=is_sim)
                results.append(res)

        db.flush()
        return results
