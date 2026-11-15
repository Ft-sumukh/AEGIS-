"""Chaos Engineering and Fault Injection API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.chaos.engine import ChaosEngine
from app.database.session import get_db
from app.security.auth import AuthUser, UserRole, require_role

router = APIRouter(prefix="/chaos", tags=["Chaos Engineering Lab"])


class InjectFaultRequest(BaseModel):
    scenario_id: str = Field(..., description="Chaos scenario ID e.g. LATENCY_SPIKE, ERROR_BURST")


class RecoverFaultRequest(BaseModel):
    run_id: str = Field(..., description="Active chaos run ID e.g. CHAOS-12345678")


@router.get("/scenarios", summary="List available chaos fault injection scenarios")
def list_scenarios(
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Returns the catalog of operational chaos experiments."""
    return ChaosEngine.list_scenarios()


@router.get("/active", summary="List active chaos simulations")
def list_active_simulations(
    user: AuthUser = Depends(require_role(UserRole.VIEWER)),
) -> list[dict[str, Any]]:
    """Returns all currently active or recently completed chaos simulations."""
    return ChaosEngine.get_active_simulations()


@router.post("/inject", summary="Inject synthetic operational fault")
def inject_fault(
    req: InjectFaultRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Injects simulated fault metrics into the telemetry stream to test closed-loop Aegis response."""
    try:
        return ChaosEngine.inject_fault(
            db=db,
            scenario_id=req.scenario_id,
            actor=user.username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/recover", summary="Restore baseline telemetry and recover from chaos fault")
def recover_fault(
    req: RecoverFaultRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
) -> dict[str, Any]:
    """Restores baseline telemetry for the given active chaos experiment."""
    try:
        return ChaosEngine.recover_fault(
            db=db,
            run_id=req.run_id,
            actor=user.username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
