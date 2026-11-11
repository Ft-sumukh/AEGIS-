"""Global operational search endpoint."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.anomaly import Anomaly
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.schemas.search import GlobalSearchResponse, SearchResultItem

router = APIRouter(prefix="/search", tags=["Global Search"])

KNOWN_SYSTEMS = [
    "checkout-service",
    "catalog-service",
    "auth-service",
    "payment-gateway",
    "notification-service",
    "postgres-cluster",
]


@router.get(
    "",
    response_model=GlobalSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Global operational entity search",
    description="Searches across incidents, investigations, systems, and anomalies for fast command-palette lookup.",
)
def global_search(
    q: str = Query(default="", min_length=1, description="Search keyword"),
    db: Session = Depends(get_db),
) -> GlobalSearchResponse:
    """Finds matching operational artifacts across all domains."""
    term = f"%{q.strip()}%"
    results: list[SearchResultItem] = []

    # 1. Incidents
    incidents = db.scalars(
        select(Incident)
        .where(
            or_(
                Incident.title.ilike(term),
                Incident.summary.ilike(term),
                Incident.category.ilike(term),
            )
        )
        .order_by(Incident.detected_at.desc())
        .limit(5)
    ).all()

    for inc in incidents:
        results.append(
            SearchResultItem(
                id=str(inc.id),
                type="incident",
                title=inc.title,
                subtitle=f"SEV-{inc.severity.value} • {inc.category} • {inc.status.value}",
                status=inc.status.value,
                severity=inc.severity.value,
                url=f"/incidents/{inc.id}",
            )
        )

    # 2. Systems
    for sys_name in KNOWN_SYSTEMS:
        if q.lower() in sys_name.lower():
            results.append(
                SearchResultItem(
                    id=sys_name,
                    type="system",
                    title=sys_name,
                    subtitle="Operational Service / Infrastructure Node",
                    status="HEALTHY",
                    url=f"/systems/{sys_name}",
                )
            )

    # 3. Investigations
    investigations = db.scalars(
        select(Investigation)
        .where(
            or_(
                Investigation.summary.ilike(term),
                Investigation.root_cause.ilike(term),
            )
        )
        .order_by(Investigation.started_at.desc())
        .limit(5)
    ).all()

    for inv in investigations:
        results.append(
            SearchResultItem(
                id=str(inv.id),
                type="investigation",
                title=f"Investigation: {inv.summary or 'Diagnostic Session'[:60]}",
                subtitle=f"Status: {inv.status.value} • Confidence: {int((inv.confidence or 0.5) * 100)}%",
                status=inv.status.value,
                url=f"/investigations/{inv.id}",
            )
        )

    # 4. Anomalies
    anomalies = db.scalars(
        select(Anomaly)
        .where(
            or_(
                Anomaly.metric_name.ilike(term),
                Anomaly.explanation.ilike(term),
            )
        )
        .order_by(Anomaly.detected_at.desc())
        .limit(5)
    ).all()

    for anom in anomalies:
        results.append(
            SearchResultItem(
                id=str(anom.id),
                type="anomaly",
                title=f"Anomaly on {anom.metric_name}",
                subtitle=f"Observed: {anom.observed_value} (Expected: {anom.expected_value}) • {anom.severity.value}",
                status=anom.status.value,
                severity=anom.severity.value,
                url=f"/analytics?metric={anom.metric_name}",
            )
        )

    return GlobalSearchResponse(
        query=q,
        total=len(results),
        results=results,
    )
