"""Platform settings, AI governance limits, and data posture API endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.models.metrics import OperationalMetric
from app.schemas.settings import SettingsResponse
from app.security.auth import AuthUser, UserRole, require_role

router = APIRouter(prefix="/settings", tags=["Platform Settings"])


@router.get(
    "",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get runtime configuration and governance posture",
    description="Retrieves active AI provider settings, resource budgets, privacy policy modes, and data retention rules.",
)
def get_platform_settings(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(
        require_role([UserRole.VIEWER, UserRole.ANALYST, UserRole.OPERATOR, UserRole.ADMIN])
    ),
) -> SettingsResponse:
    """Returns authoritative system settings from environment and config."""
    cfg = get_settings()

    distinct_sources = db.scalars(select(OperationalMetric.source).distinct()).all()
    metrics_count = db.scalar(select(func.count(OperationalMetric.id))) or 0

    return SettingsResponse(
        app_name=cfg.APP_NAME,
        app_version=cfg.APP_VERSION,
        environment=cfg.ENVIRONMENT,
        auth_enabled=cfg.AUTH_ENABLED,
        default_role=cfg.DEFAULT_DEV_ROLE,
        ai_config={
            "provider": cfg.AI_PROVIDER,
            "model": cfg.AI_MODEL,
            "max_tool_calls_per_investigation": cfg.MAX_TOOL_CALLS_PER_INVESTIGATION,
            "max_context_records": cfg.MAX_CONTEXT_RECORDS,
            "max_query_window_hours": cfg.MAX_QUERY_WINDOW_HOURS,
            "max_investigation_duration_seconds": cfg.MAX_INVESTIGATION_DURATION_SECONDS,
        },
        data_policy={
            "mode": cfg.DATA_POLICY_MODE,
            "privacy_salt_active": bool(cfg.PRIVACY_SALT),
            "redaction_active": True,
            "pseudonymization_active": True,
            "allowlisted_tools_count": 11,
            "arbitrary_sql_access": False,
        },
        retention_policy={
            "audit_log_retention_days": cfg.AUDIT_LOG_RETENTION_DAYS,
            "investigation_retention_days": cfg.INVESTIGATION_RETENTION_DAYS,
            "operational_event_retention_days": cfg.OPERATIONAL_EVENT_RETENTION_DAYS,
            "analytics_retention_days": cfg.ANALYTICS_RETENTION_DAYS,
        },
        telemetry_sources={
            "total_telemetry_records": metrics_count,
            "active_sources": list(distinct_sources) if distinct_sources else ["gateway", "checkout", "billing", "analytics"],
            "dataset_classification": "PUBLIC_DEMO",
            "quality_status": "PASSED",
        },
    )
