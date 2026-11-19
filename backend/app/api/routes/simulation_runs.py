import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.api.routes.scenarios import _scenario, effective_polling_units
from app.core.errors import AppError
from app.db.session import get_db
from app.engines.simulation import StubSimulationEngine
from app.models.equipment import EquipmentPlan
from app.models.simulation import SimulationAssumptionVersion, SimulationRun
from app.schemas.simulation import (
    SimulationAssumptionCreate,
    SimulationAssumptionResponse,
    SimulationRunCreate,
    SimulationRunResponse,
)

router = APIRouter()
admin = Depends(require_roles("system_admin"))
runner = Depends(require_roles("operations_officer", "planning_admin", "system_admin"))


@router.get("/simulation-assumptions", response_model=list[SimulationAssumptionResponse])
def list_assumptions(
    _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[SimulationAssumptionVersion]:
    return list(
        db.scalars(
            select(SimulationAssumptionVersion).order_by(
                SimulationAssumptionVersion.created_at.desc()
            )
        ).all()
    )


@router.post(
    "/simulation-assumptions",
    response_model=SimulationAssumptionResponse,
    status_code=201,
    dependencies=[admin],
)
def create_assumption(
    payload: SimulationAssumptionCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SimulationAssumptionVersion:
    assumption = SimulationAssumptionVersion(**payload.model_dump(), created_by_id=user.id)
    db.add(assumption)
    db.commit()
    db.refresh(assumption)
    return assumption


@router.post(
    "/simulation-assumptions/{assumption_id}/activate",
    response_model=SimulationAssumptionResponse,
    dependencies=[admin],
)
def activate_assumption(
    assumption_id: uuid.UUID,
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SimulationAssumptionVersion:
    assumption = db.get(SimulationAssumptionVersion, assumption_id)
    if assumption is None:
        raise AppError(
            code="simulation_assumption_not_found",
            message="Simulation assumption version was not found",
            status_code=404,
        )
    same_scope = (
        SimulationAssumptionVersion.ward_id == assumption.ward_id
        if assumption.ward_id
        else SimulationAssumptionVersion.ward_id.is_(None)
    )
    db.execute(update(SimulationAssumptionVersion).where(same_scope).values(is_active=False))
    assumption.is_active = True
    db.commit()
    db.refresh(assumption)
    return assumption


def _effective_assumption(db: Session, ward_id: uuid.UUID) -> SimulationAssumptionVersion:
    assumption = db.scalar(
        select(SimulationAssumptionVersion)
        .where(
            SimulationAssumptionVersion.is_active.is_(True),
            or_(
                SimulationAssumptionVersion.ward_id == ward_id,
                SimulationAssumptionVersion.ward_id.is_(None),
            ),
        )
        .order_by(SimulationAssumptionVersion.ward_id.is_(None))
        .limit(1)
    )
    if assumption is None:
        raise AppError(
            code="simulation_assumption_unavailable",
            message="No active simulation assumptions apply to this ward",
            status_code=409,
        )
    return assumption


@router.get("/scenarios/{scenario_id}/simulation-runs", response_model=list[SimulationRunResponse])
def list_simulation_runs(
    scenario_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[SimulationRun]:
    _scenario(db, scenario_id)
    return list(
        db.scalars(
            select(SimulationRun)
            .where(SimulationRun.scenario_id == scenario_id)
            .order_by(SimulationRun.created_at.desc())
        ).all()
    )


@router.post(
    "/scenarios/{scenario_id}/simulation-runs",
    response_model=SimulationRunResponse,
    status_code=201,
    dependencies=[runner],
)
def create_simulation_run(
    scenario_id: uuid.UUID,
    payload: SimulationRunCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SimulationRun:
    scenario = _scenario(db, scenario_id)
    assumption = _effective_assumption(db, scenario.planning_ward_id)
    equipment_plan = None
    if payload.equipment_plan_id:
        equipment_plan = db.scalar(
            select(EquipmentPlan).where(
                EquipmentPlan.id == payload.equipment_plan_id,
                EquipmentPlan.scenario_id == scenario.id,
            )
        )
        if equipment_plan is None:
            raise AppError(
                code="equipment_plan_not_found",
                message="Equipment plan does not belong to this scenario",
                status_code=422,
            )
    units = effective_polling_units(scenario.id, user, db)
    snapshot = {
        "contract_version": "1.0",
        "scenario_id": str(scenario.id),
        "scenario_revision": scenario.revision,
        "polling_units": [unit.model_dump(mode="json") for unit in units],
        "equipment_plan": (
            {
                "id": str(equipment_plan.id),
                "inventory_snapshot_id": str(equipment_plan.inventory_snapshot_id),
                "items": [
                    {
                        "polling_unit_id": str(item.polling_unit_id),
                        "equipment_type_id": str(item.equipment_type_id),
                        "allocated_quantity": item.allocated_quantity,
                    }
                    for item in equipment_plan.items
                ],
            }
            if equipment_plan
            else None
        ),
        "assumptions": {
            "id": str(assumption.id),
            "version": assumption.version,
            "voting_period_minutes": assumption.voting_period_minutes,
            "arrival_pattern": assumption.arrival_pattern,
            "average_service_minutes": assumption.average_service_minutes,
            "default_staff_count": assumption.default_staff_count,
            "equipment_uptime_ratio": assumption.equipment_uptime_ratio,
            "explanation": assumption.explanation,
        },
        "output_is_estimate": True,
    }
    engine = StubSimulationEngine()
    run = SimulationRun(
        scenario_id=scenario.id,
        equipment_plan_id=equipment_plan.id if equipment_plan else None,
        assumption_version_id=assumption.id,
        status="running",
        progress_stage="validating contract",
        engine_name=engine.name,
        engine_version=engine.version,
        input_snapshot=snapshot,
        created_by_id=user.id,
    )
    db.add(run)
    db.flush()
    result = engine.run(snapshot)
    run.status = result.status
    run.progress_stage = "contract placeholder complete"
    run.result = result.model_dump(mode="json")
    run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run


@router.get("/simulation-runs/{run_id}", response_model=SimulationRunResponse)
def get_simulation_run(
    run_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> SimulationRun:
    run = db.get(SimulationRun, run_id)
    if run is None:
        raise AppError(
            code="simulation_run_not_found", message="Simulation run was not found", status_code=404
        )
    return run


@router.post(
    "/simulation-runs/{run_id}/cancel",
    response_model=SimulationRunResponse,
    dependencies=[runner],
)
def cancel_simulation_run(
    run_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> SimulationRun:
    run = get_simulation_run(run_id, user, db)
    if run.status in {"queued", "running"}:
        run.status = "cancelled"
        run.progress_stage = "cancelled"
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
    return run
