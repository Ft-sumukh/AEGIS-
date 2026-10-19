"""Health and readiness check endpoints for Aegis."""

from fastapi import APIRouter, Depends, Response, status

from app.config import Settings, get_settings
from app.database.session import check_database_connection
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application liveness probe",
    description="Returns basic application operational status. Always fast and non-blocking.",
)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Liveness probe to confirm backend process is alive and accepting requests."""
    return HealthResponse(
        status="healthy",
        service=f"{settings.APP_NAME.lower()}-backend",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Application readiness probe",
    description="Checks downstream dependencies including PostgreSQL database connection.",
)
def get_readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    """Readiness probe to confirm downstream dependencies (PostgreSQL) are operational."""
    db_ok, latency_ms, error = check_database_connection()

    if db_ok:
        return ReadinessResponse(
            status="ready",
            service=f"{settings.APP_NAME.lower()}-backend",
            version=settings.APP_VERSION,
            database="connected",
            latency_ms=round(latency_ms, 2),
            detail=None,
        )

    # Degraded / Service Unavailable if database cannot be reached
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="degraded",
        service=f"{settings.APP_NAME.lower()}-backend",
        version=settings.APP_VERSION,
        database="unreachable",
        latency_ms=round(latency_ms, 2),
        detail=error or "Database connectivity check failed",
    )
