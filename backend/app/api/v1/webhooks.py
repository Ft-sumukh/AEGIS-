"""External Webhook Subscriptions and Alert Dispatcher API router."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.webhook import WebhookSubscription
from app.security.auth import AuthUser, UserRole, require_role
from app.webhooks.dispatcher import WebhookDispatcher

router = APIRouter(prefix="/webhooks", tags=["External Webhooks & Alert Dispatching"])


class CreateWebhookRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    url: str = Field(..., min_length=8, max_length=500)
    secret_token: str | None = Field(None, max_length=255)
    target_type: str = Field("SLACK", pattern="^(SLACK|PAGERDUTY|GENERIC_WEBHOOK|STATUSPAGE)$")
    subscribed_events: list[str] = Field(
        default_factory=lambda: [
            "INCIDENT_CREATED",
            "INCIDENT_RESOLVED",
            "ACTION_APPROVED",
            "SLO_BUDGET_BURNING",
        ]
    )


def _serialize_subscription(sub: WebhookSubscription) -> dict[str, Any]:
    return {
        "id": str(sub.id),
        "company_id": str(sub.company_id),
        "name": sub.name,
        "url": sub.url,
        "target_type": sub.target_type,
        "subscribed_events": sub.subscribed_events,
        "is_active": sub.is_active,
        "last_dispatched_at": sub.last_dispatched_at.isoformat() if sub.last_dispatched_at else None,
        "last_status_code": sub.last_status_code,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


@router.get("", summary="List all webhook subscriptions")
def list_webhooks(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Returns all registered webhook notification targets."""
    query = select(WebhookSubscription)
    if user.company_id:
        query = query.where(WebhookSubscription.company_id == user.company_id)

    subs = db.execute(query).scalars().all()
    return [_serialize_subscription(s) for s in subs]


@router.post("", summary="Register a new webhook subscription", status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: CreateWebhookRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Registers an external webhook endpoint for incident and SLO alerts."""
    company_id = user.company_id
    if not company_id:
        comp = db.query(Company).first()
        company_id = comp.id if comp else uuid.uuid4()

    sub = WebhookSubscription(
        id=uuid.uuid4(),
        company_id=company_id,
        name=payload.name,
        url=payload.url,
        secret_token=payload.secret_token,
        target_type=payload.target_type,
        subscribed_events=payload.subscribed_events,
        is_active=True,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _serialize_subscription(sub)


@router.post("/{webhook_id}/test", summary="Trigger a test alert dispatch to webhook")
def test_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Sends a verified test payload to validate endpoint URL and HMAC signatures."""
    sub = db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription '{webhook_id}' not found.",
        )

    test_payload = {
        "id": str(uuid.uuid4()),
        "title": "Aegis Verified Test Alert",
        "severity": "CRITICAL",
        "summary": "This is a synthetic verification probe dispatched by the Aegis SRE Engine.",
        "affected_systems": ["checkout-service", "api-gateway"],
    }

    result = WebhookDispatcher.dispatch_subscription(
        subscription=sub,
        event_type="AEGIS_TEST_PROBE",
        payload=test_payload,
        is_simulation_mode=True,
    )
    db.commit()
    return result


@router.delete("/{webhook_id}", summary="Delete a webhook subscription")
def delete_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Removes a registered webhook subscription."""
    sub = db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription '{webhook_id}' not found.",
        )

    db.delete(sub)
    db.commit()
    return {"message": f"Webhook subscription '{webhook_id}' deleted successfully.", "deleted_id": str(webhook_id)}
