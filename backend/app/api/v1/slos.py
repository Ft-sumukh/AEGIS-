"""Service Level Objectives (SLO) & Multi-Window Error Budget Burn-Rate API router."""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analytics.slo_service import SLOService
from app.database.session import get_db
from app.models.company import Company
from app.models.slo import ServiceLevelObjective
from app.security.auth import AuthUser, UserRole, require_role

router = APIRouter(prefix="/slos", tags=["Service Level Objectives & Error Budgets"])


class CreateSLORequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    service_name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    target_percentage: float = Field(..., ge=90.0, le=99.999)
    sli_metric_name: str = Field(..., min_length=2, max_length=100)
    sli_type: str = Field("AVAILABILITY", pattern="^(AVAILABILITY|LATENCY|ERROR_RATE|THROUGHPUT)$")
    time_window_days: int = Field(30, ge=1, le=90)


class EvaluateSLORequest(BaseModel):
    override_recent_error_rate: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Simulate or force a specific error percentage (e.g. 2.5 for 2.5% error rate)",
    )


@router.get("", summary="List all Service Level Objectives")
def list_slos(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Returns all registered SLOs with live multi-window burn rates and budget consumption."""
    return SLOService.list_slos(db, company_id=user.company_id)


@router.get("/summary", summary="Get aggregate SLO health summary")
def get_slo_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> dict[str, Any]:
    """Returns high-level error budget metrics across all enterprise services."""
    slos = SLOService.list_slos(db, company_id=user.company_id)
    total = len(slos)
    healthy = sum(1 for s in slos if s["status"] == "HEALTHY")
    warning = sum(1 for s in slos if s["status"] == "WARNING")
    burning = sum(1 for s in slos if s["status"] == "BURNING")
    exhausted = sum(1 for s in slos if s["status"] == "EXHAUSTED")
    avg_budget = (
        round(sum(s["error_budget_remaining_percent"] for s in slos) / total, 2)
        if total > 0
        else 100.0
    )

    return {
        "total_slos": total,
        "healthy_count": healthy,
        "warning_count": warning,
        "burning_count": burning,
        "exhausted_count": exhausted,
        "average_error_budget_percent": avg_budget,
    }


@router.get("/{slo_id}", summary="Get SLO details by ID")
def get_slo(
    slo_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> dict[str, Any]:
    """Retrieves detailed operational metrics and burn rates for a specific SLO."""
    slo = SLOService.get_slo(db, slo_id)
    if not slo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SLO '{slo_id}' not found.",
        )
    return slo


@router.post("/{slo_id}/evaluate", summary="Trigger on-demand SLO evaluation")
def evaluate_slo(
    slo_id: uuid.UUID,
    payload: EvaluateSLORequest | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Evaluates multi-window burn rate (1h/6h/24h) and updates error budget."""
    try:
        override = payload.override_recent_error_rate if payload else None
        result = SLOService.evaluate_slo(db, slo_id, override_recent_error_rate=override)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", summary="Create a new Service Level Objective", status_code=status.HTTP_201_CREATED)
def create_slo(
    payload: CreateSLORequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Registers a new Service Level Objective for a target microservice."""
    company_id = user.company_id
    if not company_id:
        comp = db.query(Company).first()
        company_id = comp.id if comp else uuid.uuid4()

    new_slo = ServiceLevelObjective(
        id=uuid.uuid4(),
        company_id=company_id,
        name=payload.name,
        service_name=payload.service_name,
        description=payload.description,
        target_percentage=payload.target_percentage,
        sli_metric_name=payload.sli_metric_name,
        sli_type=payload.sli_type,
        time_window_days=payload.time_window_days,
        current_sli=payload.target_percentage + 0.05,
        error_budget_remaining_percent=100.0,
        burn_rate_1h=1.0,
        burn_rate_6h=1.0,
        burn_rate_24h=1.0,
        status="HEALTHY",
        metadata_info={"created_by": user.user_id},
    )
    db.add(new_slo)
    db.commit()
    db.refresh(new_slo)
    return SLOService.to_dict(new_slo)
