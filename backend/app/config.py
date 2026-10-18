"""Centralized application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Info
    APP_NAME: str = Field(default="Aegis", description="Application service name")
    APP_VERSION: str = Field(default="0.1.0", description="SemVer application version")
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development, staging, production, test",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Structured logging severity level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    # API Routing
    API_V1_PREFIX: str = Field(default="/api/v1", description="Prefix for API version 1 endpoints")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="Backend bind host")
    BACKEND_PORT: int = Field(default=8000, description="Backend bind port")

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://aegis_user:aegis_dev_password@localhost:5432/aegis_db",
        description="SQLAlchemy database connection URL",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Pool acquisition timeout in seconds")

    # Security & CORS
    SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="Secret key for cryptographical signing",
    )
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for Cross-Origin Resource Sharing",
    )

    # AI Provider (Foundation for future AI modules)
    AI_PROVIDER: str = Field(
        default="mock",
        description="AI provider identifier (mock, openai, anthropic, google)",
    )
    AI_MODEL: str = Field(
        default="claude-3-5-sonnet",
        description="Target model identifier",
    )
    AI_API_KEY: str = Field(
        default="",
        description="API key for AI provider (empty in development/mock)",
    )

    # Privacy, Governance & Data Minimization
    DATA_POLICY_MODE: str = Field(
        default="STANDARD",
        description="AI data governance mode: STRICT, STANDARD, or DEVELOPMENT",
    )
    PRIVACY_SALT: str = Field(
        default="aegis-privacy-salt-secret-change-in-production",
        description="Secret salt used for deterministic HMAC pseudonymization",
    )

    # Resource & Investigation Limits
    MAX_QUERY_WINDOW_HOURS: int = Field(
        default=24,
        description="Maximum time window in hours accessible per tool invocation",
    )
    MAX_RECORDS_PER_TOOL_CALL: int = Field(
        default=50,
        description="Maximum records returned by any single operational tool call",
    )
    MAX_CONTEXT_RECORDS: int = Field(
        default=200,
        description="Maximum total operational evidence records retained in active context",
    )
    MAX_TOOL_CALLS_PER_INVESTIGATION: int = Field(
        default=20,
        description="Maximum tool calls permitted per diagnostic investigation run",
    )
    MAX_INVESTIGATION_DURATION_SECONDS: int = Field(
        default=120,
        description="Hard deadline in seconds for an automated investigation run",
    )

    # Data Retention Policies (Days)
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=90, description="Audit log retention window in days")
    INVESTIGATION_RETENTION_DAYS: int = Field(default=180, description="Investigation findings retention in days")
    OPERATIONAL_EVENT_RETENTION_DAYS: int = Field(default=30, description="Operational event retention in days")
    ANALYTICS_RETENTION_DAYS: int = Field(default=60, description="Raw telemetry analytics retention in days")

    # Authentication & Server-Side RBAC
    AUTH_ENABLED: bool = Field(
        default=False,
        description="When False, permits development access with default role fallback; True strictly enforces bearer credentials",
    )
    DEFAULT_DEV_ROLE: str = Field(
        default="OPERATOR",
        description="Default role assigned to unauthenticated dev requests when AUTH_ENABLED=False",
    )

    # Action & Human Approval Engine (Group 9)
    ACTION_EXECUTION_MODE: str = Field(
        default="SIMULATED",
        description="Action execution mode: SIMULATED (default). Real cloud execution is strictly prevented.",
    )
    ACTION_APPROVAL_TTL_MINUTES: int = Field(
        default=30,
        description="Action approval validity window in minutes before automatic expiration.",
    )
    ACTION_VERIFICATION_WINDOW_SECONDS: int = Field(
        default=60,
        description="Observation window in seconds for operational metric verification.",
    )
    ENFORCE_SEPARATION_OF_DUTIES: bool = Field(
        default=False,
        description="When True, prevents requester from approving their own high-risk actions.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Normalize CORS origins from JSON string, comma-separated string, or list."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v]
        return ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
