"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.actions import router as actions_router
from app.api.v1.analytics import (
    candidates_router as incident_candidates_router,
    router as analytics_router,
)
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.audit import router as audit_router
from app.api.v1.chaos import router as chaos_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.data import router as data_router
from app.api.v1.health import router as health_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.overview import router as overview_router
from app.api.v1.postmortem import router as postmortem_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.runbooks import router as runbooks_router
from app.api.v1.search import router as search_router
from app.api.v1.services import router as services_router
from app.api.v1.settings import router as settings_router
from app.api.v1.slos import router as slos_router
from app.api.v1.stream import router as stream_router
from app.api.v1.systems import router as systems_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.traces import router as traces_router
from app.api.v1.webhooks import router as webhooks_router

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(overview_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(postmortem_router)
api_v1_router.include_router(runbooks_router)
api_v1_router.include_router(investigations_router)
api_v1_router.include_router(recommendations_router)
api_v1_router.include_router(actions_router)
api_v1_router.include_router(systems_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(traces_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(data_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(incident_candidates_router)
api_v1_router.include_router(stream_router)
api_v1_router.include_router(chaos_router)
api_v1_router.include_router(slos_router)
api_v1_router.include_router(copilot_router)
api_v1_router.include_router(webhooks_router)
