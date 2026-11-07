"""Pydantic schemas for platform runtime settings and posture."""

from typing import Any
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    """Runtime platform configuration, AI governance limits, and data retention rules."""

    app_name: str
    app_version: str
    environment: str
    auth_enabled: bool
    default_role: str
    ai_config: dict[str, Any]
    data_policy: dict[str, Any]
    retention_policy: dict[str, Any]
    telemetry_sources: dict[str, Any]
