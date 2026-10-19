"""Automated tests for health, readiness, configuration, and middleware."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_application


def test_health_endpoint_success(client: TestClient) -> None:
    """Verify GET /api/v1/health returns HTTP 200 with required structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data
    assert data["service"] == "aegistest-backend"
    assert data["version"] == "0.2.0-test"


def test_request_id_middleware_header(client: TestClient) -> None:
    """Verify responses include request correlation ID headers."""
    custom_id = "test-request-id-12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    assert "X-Response-Time-Ms" in response.headers


def test_readiness_endpoint_healthy(client: TestClient) -> None:
    """Verify readiness returns 200 when database check succeeds."""
    with patch("app.api.v1.health.check_database_connection", return_value=(True, 1.25, None)):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["latency_ms"] == 1.25
        assert data["detail"] is None


def test_readiness_endpoint_degraded(client: TestClient) -> None:
    """Verify readiness returns 503 when database check fails."""
    with patch(
        "app.api.v1.health.check_database_connection",
        return_value=(False, 15.0, "Connection refused"),
    ):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unreachable"
        assert "Connection refused" in data["detail"]


def test_configuration_loading() -> None:
    """Verify Settings parses configuration and parses CORS origins."""
    settings = Settings(
        APP_NAME="CustomAegis",
        CORS_ORIGINS='["http://localhost:3000","http://example.com"]',
    )
    assert settings.APP_NAME == "CustomAegis"
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://example.com" in settings.CORS_ORIGINS


def test_app_factory() -> None:
    """Verify application factory initializes without error."""
    new_app = create_application()
    assert new_app.title.startswith("Aegis")
