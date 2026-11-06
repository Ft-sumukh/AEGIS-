"""Security and Operational Audit Log API endpoints."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.database.session import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogRead
from app.schemas.common import PaginatedResponse
from app.security.auth import AuthUser, UserRole, require_role
from app.security.sanitizer import DataSanitizer

logger = get_logger("aegis.api.audit")
router = APIRouter(prefix="/audit", tags=["Security & Audit"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogRead],
    status_code=status.HTTP_200_OK,
    summary="List security and operational audit logs",
    description="Retrieves append-only, tamper-evident audit logs with automatic metadata credential scrubbing.",
)
def list_audit_logs(
    action: str | None = Query(default=None, description="Filter by audit action"),
    actor_id: str | None = Query(default=None, description="Filter by actor identifier"),
    resource_type: str | None = Query(default=None, description="Filter by target resource type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> PaginatedResponse[AuditLogRead]:
    """Lists audit logs with metadata sanitization."""
    try:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        count_query = select(func.count(AuditLog.id))
        if action:
            count_query = count_query.where(AuditLog.action == action)
        if actor_id:
            count_query = count_query.where(AuditLog.actor_id == actor_id)
        if resource_type:
            count_query = count_query.where(AuditLog.resource_type == resource_type)

        total = db.scalar(count_query) or 0
        items = db.scalars(
            query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        ).all()

        sanitized_items: list[AuditLogRead] = []
        for item in items:
            read_item = AuditLogRead.model_validate(item)
            # Ensure metadata credentials remain scrubbed as per Group 7 policy
            read_item.audit_metadata = DataSanitizer.sanitize_dict(read_item.audit_metadata)
            sanitized_items.append(read_item)

        return PaginatedResponse(
            items=sanitized_items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception(f"Error querying audit logs: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security audit logs.",
        ) from exc
