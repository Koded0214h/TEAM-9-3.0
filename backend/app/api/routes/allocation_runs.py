import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.api.routes.scenarios import _scenario, effective_polling_units
from app.core.errors import AppError
from app.db.session import get_db
from app.engines.allocation import StubAllocationEngine
from app.models.allocation import AllocationRun
from app.schemas.allocation import AllocationRunCreate, AllocationRunResponse

router = APIRouter()
runner_roles = Depends(require_roles("planning_admin", "system_admin"))


@router.get("/scenarios/{scenario_id}/allocation-runs", response_model=list[AllocationRunResponse])
def list_allocation_runs(
    scenario_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[AllocationRun]:
    _scenario(db, scenario_id)
    return list(
        db.scalars(
            select(AllocationRun)
            .where(AllocationRun.scenario_id == scenario_id)
            .order_by(AllocationRun.created_at.desc())
        ).all()
    )


@router.post(
    "/scenarios/{scenario_id}/allocation-runs",
    response_model=AllocationRunResponse,
    status_code=201,
    dependencies=[runner_roles],
)
def create_allocation_run(
    scenario_id: uuid.UUID,
    payload: AllocationRunCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AllocationRun:
    scenario = _scenario(db, scenario_id)
    units = effective_polling_units(scenario_id, user, db)
    snapshot = {
        "contract_version": "1.0",
        "scenario_id": str(scenario.id),
        "scenario_revision": scenario.revision,
        "planning_ward_id": str(scenario.planning_ward_id),
        "baseline_polling_dataset_id": str(scenario.baseline_polling_dataset_id),
        "baseline_geography_dataset_id": str(scenario.baseline_geography_dataset_id),
        "polling_units": [unit.model_dump(mode="json") for unit in units],
        "objective_weights": payload.objective_weights,
        "constraints": payload.constraints,
    }
    engine = StubAllocationEngine()
    run = AllocationRun(
        scenario_id=scenario.id,
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


@router.get("/allocation-runs/{run_id}", response_model=AllocationRunResponse)
def get_allocation_run(
    run_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> AllocationRun:
    run = db.get(AllocationRun, run_id)
    if run is None:
        raise AppError(
            code="allocation_run_not_found", message="Allocation run was not found", status_code=404
        )
    return run


@router.post(
    "/allocation-runs/{run_id}/cancel",
    response_model=AllocationRunResponse,
    dependencies=[runner_roles],
)
def cancel_allocation_run(
    run_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> AllocationRun:
    run = get_allocation_run(run_id, _, db)
    if run.status in {"queued", "running"}:
        run.status = "cancelled"
        run.progress_stage = "cancelled"
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
    return run


@router.post(
    "/allocation-runs/{run_id}/select",
    response_model=AllocationRunResponse,
    dependencies=[runner_roles],
)
def select_allocation_run(
    run_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> AllocationRun:
    run = get_allocation_run(run_id, _, db)
    if run.status != "succeeded":
        raise AppError(
            code="allocation_run_not_selectable",
            message="Only successful real engine results can be selected",
            status_code=409,
        )
    db.execute(
        update(AllocationRun)
        .where(AllocationRun.scenario_id == run.scenario_id)
        .values(is_selected=False)
    )
    run.is_selected = True
    db.commit()
    db.refresh(run)
    return run
