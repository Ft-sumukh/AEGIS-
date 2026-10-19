"""Aegis AI Operations Intelligence Platform - Backend API Entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_v1_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.security.headers import SecurityHeadersMiddleware

logger = get_logger("aegis.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context for startup and graceful shutdown hooks."""
    settings = get_settings()
    setup_logging(
        log_level=settings.LOG_LEVEL,
        environment=settings.ENVIRONMENT,
        service_name=f"{settings.APP_NAME.lower()}-backend",
    )
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME} v{settings.APP_VERSION}")


def create_application() -> FastAPI:
    """FastAPI application factory with middleware, security headers, and routes."""
    settings = get_settings()

    application = FastAPI(
        title=f"{settings.APP_NAME} Operations Intelligence API",
        description="Privacy-preserving AI Operations Intelligence Platform backend services.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS Configuration
    # Local development allows frontend origins; production relies on explicit environment configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # HTTP Defensive Security Headers Middleware
    application.add_middleware(SecurityHeadersMiddleware)

    # Request ID and tracing correlation middleware
    application.add_middleware(RequestCorrelationMiddleware)

    # Sanitized Global Exception Handler (prevents stack traces & secrets leakage)
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            f"Unhandled server error on {request.method} {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "An internal operational error occurred. Diagnostic details have been logged securely.",
                "code": "INTERNAL_SERVER_ERROR",
            },
        )

    # Mount API v1 endpoints
    application.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()
