import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.api.routes.comparisons import compare_scenario
from app.api.routes.scenarios import _scenario
from app.core.errors import AppError
from app.db.session import get_db
from app.models.allocation import AllocationRun
from app.models.exports import ExportJob
from app.models.geography import DatasetVersion
from app.models.simulation import SimulationRun
from app.schemas.exports import ExportCreate, ExportJobResponse
from app.services.exports import render_comparison_csv, render_json_export

router = APIRouter()
exporter = Depends(require_roles("planning_admin", "operations_officer", "system_admin"))


def _export(db: Session, export_id: uuid.UUID) -> ExportJob:
    job = db.get(ExportJob, export_id)
    if job is None:
        raise AppError(code="export_not_found", message="Export was not found", status_code=404)
    return job


@router.post(
    "/scenarios/{scenario_id}/exports",
    response_model=ExportJobResponse,
    status_code=201,
    dependencies=[exporter],
)
def create_export(
    scenario_id: uuid.UUID,
    request: ExportCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ExportJob:
    scenario = _scenario(db, scenario_id)
    comparison = compare_scenario(scenario.id, user, db)
    datasets = list(
        db.scalars(
            select(DatasetVersion).where(
                DatasetVersion.id.in_(
                    [scenario.baseline_polling_dataset_id, scenario.baseline_geography_dataset_id]
                )
            )
        ).all()
    )
    allocation = db.scalar(
        select(AllocationRun)
        .where(AllocationRun.scenario_id == scenario.id)
        .order_by(AllocationRun.created_at.desc())
        .limit(1)
    )
    simulation = db.scalar(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(SimulationRun.created_at.desc())
        .limit(1)
    )
    generated_at = datetime.now(UTC)
    payload = {
        "export_version": "1.0",
        "generated_at": generated_at.isoformat(),
        "generated_by": str(user.id),
        "scenario": {
            "id": str(scenario.id),
            "name": scenario.name,
            "description": scenario.description,
            "status": scenario.status,
            "revision": scenario.revision,
        },
        "datasets": [
            {
                "id": str(dataset.id),
                "type": dataset.dataset_type,
                "name": dataset.name,
                "version": dataset.version,
                "source": dataset.source,
                "classification": dataset.classification,
                "checksum": dataset.checksum,
            }
            for dataset in datasets
        ],
        "comparison": comparison.model_dump(mode="json"),
        "allocation_run": (
            {
                "id": str(allocation.id),
                "status": allocation.status,
                "engine": allocation.engine_name,
                "engine_version": allocation.engine_version,
                "result": allocation.result,
            }
            if allocation
            else None
        ),
        "simulation_run": (
            {
                "id": str(simulation.id),
                "status": simulation.status,
                "engine": simulation.engine_name,
                "engine_version": simulation.engine_version,
                "assumptions": simulation.input_snapshot.get("assumptions"),
                "result": simulation.result,
            }
            if simulation
            else None
        ),
        "warnings": [
            (
                "Sample, synthetic, and estimated values are identified by dataset "
                "classification and coordinate source."
            ),
            "Planning recommendations do not alter official polling-unit or voter assignments.",
        ],
    }
    if request.format == "json":
        content = render_json_export(payload)
        content_type = "application/json"
    else:
        content = render_comparison_csv(payload)
        content_type = "text/csv"
    job = ExportJob(
        scenario_id=scenario.id,
        format=request.format,
        status="succeeded",
        filename=f"repelect-scenario-{scenario.id}.{request.format}",
        content_type=content_type,
        content=content,
        created_by_id=user.id,
        completed_at=generated_at,
        expires_at=generated_at + timedelta(hours=24),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/exports/{export_id}", response_model=ExportJobResponse)
def get_export(
    export_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ExportJob:
    return _export(db, export_id)


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Response:
    job = _export(db, export_id)
    if job.expires_at <= datetime.now(UTC):
        raise AppError(
            code="export_expired", message="Export download has expired", status_code=410
        )
    if job.status != "succeeded" or job.content is None:
        raise AppError(code="export_not_ready", message="Export is not ready", status_code=409)
    return Response(
        content=job.content,
        media_type=job.content_type,
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )
