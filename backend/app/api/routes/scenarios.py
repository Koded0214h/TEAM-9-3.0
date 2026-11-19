import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.geography import DatasetVersion, PollingUnit, Ward
from app.models.scenarios import Scenario, ScenarioPollingUnitChange, ScenarioRevision
from app.schemas.scenarios import (
    EffectivePollingUnit,
    PollingUnitChangeCreate,
    PollingUnitChangeResponse,
    PollingUnitChangeUpdate,
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
)
from app.services.scenarios import ensure_point_in_scenario, ensure_revision, record_revision

router = APIRouter()
editor = Depends(require_roles("planning_admin", "system_admin"))


def _scenario(db: Session, scenario_id: uuid.UUID) -> Scenario:
    scenario = db.scalar(
        select(Scenario).where(Scenario.id == scenario_id, Scenario.is_deleted.is_(False))
    )
    if scenario is None:
        raise AppError(code="scenario_not_found", message="Scenario was not found", status_code=404)
    return scenario


def _active_dataset(db: Session, dataset_type: str) -> DatasetVersion:
    dataset = db.scalar(
        select(DatasetVersion).where(
            DatasetVersion.dataset_type == dataset_type, DatasetVersion.is_active.is_(True)
        )
    )
    if dataset is None:
        raise AppError(
            code="baseline_unavailable",
            message=f"No active {dataset_type} dataset is available",
            status_code=409,
        )
    return dataset


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    include_archived: bool = False,
) -> list[Scenario]:
    query = select(Scenario).where(Scenario.is_deleted.is_(False))
    if not include_archived:
        query = query.where(Scenario.status != "archived")
    return list(db.scalars(query.order_by(Scenario.updated_at.desc())).all())


@router.post("", response_model=ScenarioResponse, status_code=201, dependencies=[editor])
def create_scenario(
    payload: ScenarioCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Scenario:
    geography = _active_dataset(db, "administrative_geography")
    polling = _active_dataset(db, "polling_units")
    ward = db.scalar(
        select(Ward).where(Ward.id == payload.planning_ward_id, Ward.dataset_id == geography.id)
    )
    if ward is None:
        raise AppError(
            code="planning_ward_not_found",
            message="Planning ward is not in the active geography dataset",
            status_code=422,
        )
    scenario = Scenario(
        **payload.model_dump(),
        baseline_polling_dataset_id=polling.id,
        baseline_geography_dataset_id=geography.id,
        created_by_id=user.id,
    )
    db.add(scenario)
    db.flush()
    db.add(
        ScenarioRevision(
            scenario_id=scenario.id,
            revision=1,
            action="created",
            snapshot={"name": scenario.name, "planning_ward_id": str(scenario.planning_ward_id)},
            actor_id=user.id,
        )
    )
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Scenario:
    return _scenario(db, scenario_id)


@router.patch("/{scenario_id}", response_model=ScenarioResponse, dependencies=[editor])
def update_scenario(
    scenario_id: uuid.UUID,
    payload: ScenarioUpdate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Scenario:
    scenario = _scenario(db, scenario_id)
    ensure_revision(scenario, payload.expected_revision)
    changes = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    for field, value in changes.items():
        setattr(scenario, field, value)
    record_revision(db, scenario, user.id, "metadata_updated", changes)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}", status_code=204, dependencies=[editor])
def delete_scenario(
    scenario_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    expected_revision: Annotated[int, Query(ge=1)],
) -> None:
    scenario = _scenario(db, scenario_id)
    ensure_revision(scenario, expected_revision)
    scenario.is_deleted = True
    record_revision(db, scenario, user.id, "soft_deleted", {})
    db.commit()


@router.post(
    "/{scenario_id}/duplicate",
    response_model=ScenarioResponse,
    status_code=201,
    dependencies=[editor],
)
def duplicate_scenario(
    scenario_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Scenario:
    source = _scenario(db, scenario_id)
    duplicate = Scenario(
        name=f"{source.name} (copy)",
        description=source.description,
        planning_ward_id=source.planning_ward_id,
        baseline_polling_dataset_id=source.baseline_polling_dataset_id,
        baseline_geography_dataset_id=source.baseline_geography_dataset_id,
        created_by_id=user.id,
    )
    db.add(duplicate)
    db.flush()
    for change in source.changes:
        db.add(
            ScenarioPollingUnitChange(
                scenario_id=duplicate.id,
                baseline_polling_unit_id=change.baseline_polling_unit_id,
                change_type=change.change_type,
                code=change.code,
                name=change.name,
                address=change.address,
                location=change.location,
                latitude=change.latitude,
                longitude=change.longitude,
                registered_voters=change.registered_voters,
                reason=f"Copied from scenario {source.id}: {change.reason}",
                created_by_id=user.id,
            )
        )
    db.add(
        ScenarioRevision(
            scenario_id=duplicate.id,
            revision=1,
            action="duplicated",
            snapshot={"source_scenario_id": str(source.id)},
            actor_id=user.id,
        )
    )
    db.commit()
    db.refresh(duplicate)
    return duplicate


@router.get("/{scenario_id}/polling-unit-changes", response_model=list[PollingUnitChangeResponse])
def list_polling_unit_changes(
    scenario_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[ScenarioPollingUnitChange]:
    scenario = _scenario(db, scenario_id)
    return scenario.changes


@router.post(
    "/{scenario_id}/polling-unit-changes",
    response_model=PollingUnitChangeResponse,
    status_code=201,
    dependencies=[editor],
)
def create_polling_unit_change(
    scenario_id: uuid.UUID,
    payload: PollingUnitChangeCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioPollingUnitChange:
    scenario = _scenario(db, scenario_id)
    ensure_revision(scenario, payload.expected_revision)
    baseline = None
    if payload.baseline_polling_unit_id:
        baseline = db.scalar(
            select(PollingUnit).where(
                PollingUnit.id == payload.baseline_polling_unit_id,
                PollingUnit.dataset_id == scenario.baseline_polling_dataset_id,
                PollingUnit.ward_id == scenario.planning_ward_id,
            )
        )
        if baseline is None:
            raise AppError(
                code="baseline_polling_unit_not_found",
                message="Polling unit is not part of this scenario baseline",
                status_code=422,
            )
        existing = db.scalar(
            select(ScenarioPollingUnitChange.id).where(
                ScenarioPollingUnitChange.scenario_id == scenario.id,
                ScenarioPollingUnitChange.baseline_polling_unit_id == baseline.id,
            )
        )
        if existing:
            raise AppError(
                code="polling_unit_change_exists",
                message="This baseline polling unit already has a scenario change",
                status_code=409,
            )
    location = None
    if payload.latitude is not None and payload.longitude is not None:
        location = ensure_point_in_scenario(db, scenario, payload.latitude, payload.longitude)
    change = ScenarioPollingUnitChange(
        scenario_id=scenario.id,
        baseline_polling_unit_id=payload.baseline_polling_unit_id,
        change_type=payload.change_type,
        code=payload.code,
        name=payload.name,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        registered_voters=payload.registered_voters,
        reason=payload.reason,
        location=location,
        created_by_id=user.id,
    )
    db.add(change)
    db.flush()
    record_revision(
        db,
        scenario,
        user.id,
        "polling_unit_change_created",
        {"change_id": str(change.id), "change_type": change.change_type},
    )
    db.commit()
    db.refresh(change)
    return change


@router.patch(
    "/{scenario_id}/polling-unit-changes/{change_id}",
    response_model=PollingUnitChangeResponse,
    dependencies=[editor],
)
def update_polling_unit_change(
    scenario_id: uuid.UUID,
    change_id: uuid.UUID,
    payload: PollingUnitChangeUpdate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioPollingUnitChange:
    scenario = _scenario(db, scenario_id)
    ensure_revision(scenario, payload.expected_revision)
    change = db.scalar(
        select(ScenarioPollingUnitChange).where(
            ScenarioPollingUnitChange.id == change_id,
            ScenarioPollingUnitChange.scenario_id == scenario.id,
        )
    )
    if change is None:
        raise AppError(
            code="polling_unit_change_not_found",
            message="Polling-unit change was not found",
            status_code=404,
        )
    updates = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    latitude = updates.get("latitude", change.latitude)
    longitude = updates.get("longitude", change.longitude)
    if "latitude" in updates or "longitude" in updates:
        if latitude is None or longitude is None:
            raise AppError(
                code="incomplete_coordinates",
                message="Both latitude and longitude are required",
                status_code=422,
            )
        change.location = ensure_point_in_scenario(db, scenario, latitude, longitude)
    for field, value in updates.items():
        setattr(change, field, value)
    record_revision(
        db,
        scenario,
        user.id,
        "polling_unit_change_updated",
        {"change_id": str(change.id), "fields": sorted(updates)},
    )
    db.commit()
    db.refresh(change)
    return change


@router.delete(
    "/{scenario_id}/polling-unit-changes/{change_id}",
    status_code=204,
    dependencies=[editor],
)
def delete_polling_unit_change(
    scenario_id: uuid.UUID,
    change_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    expected_revision: Annotated[int, Query(ge=1)],
) -> None:
    scenario = _scenario(db, scenario_id)
    ensure_revision(scenario, expected_revision)
    change = db.scalar(
        select(ScenarioPollingUnitChange).where(
            ScenarioPollingUnitChange.id == change_id,
            ScenarioPollingUnitChange.scenario_id == scenario.id,
        )
    )
    if change is None:
        raise AppError(
            code="polling_unit_change_not_found",
            message="Polling-unit change was not found",
            status_code=404,
        )
    snapshot = {"change_id": str(change.id), "change_type": change.change_type}
    db.delete(change)
    record_revision(db, scenario, user.id, "polling_unit_change_removed", snapshot)
    db.commit()


@router.get("/{scenario_id}/effective-polling-units", response_model=list[EffectivePollingUnit])
def effective_polling_units(
    scenario_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[EffectivePollingUnit]:
    scenario = _scenario(db, scenario_id)
    baseline_units = list(
        db.scalars(
            select(PollingUnit).where(
                PollingUnit.dataset_id == scenario.baseline_polling_dataset_id,
                PollingUnit.ward_id == scenario.planning_ward_id,
            )
        ).all()
    )
    by_baseline = {
        change.baseline_polling_unit_id: change
        for change in scenario.changes
        if change.baseline_polling_unit_id is not None
    }
    result = []
    for unit in baseline_units:
        change = by_baseline.get(unit.id)
        result.append(
            EffectivePollingUnit(
                id=unit.id,
                baseline_polling_unit_id=unit.id,
                change_id=change.id if change else None,
                source="modified" if change else "official",
                code=(change.code if change and change.code else unit.code),
                name=(change.name if change and change.name else unit.name),
                address=(change.address if change and change.address else unit.address),
                latitude=(
                    change.latitude if change and change.latitude is not None else unit.latitude
                ),
                longitude=(
                    change.longitude if change and change.longitude is not None else unit.longitude
                ),
                status="inactive"
                if change and change.change_type == "deactivated"
                else unit.status,
                registered_voters=(
                    change.registered_voters
                    if change and change.registered_voters is not None
                    else unit.registered_voters
                ),
            )
        )
    for change in scenario.changes:
        if change.change_type == "proposed_new":
            result.append(
                EffectivePollingUnit(
                    id=change.id,
                    baseline_polling_unit_id=None,
                    change_id=change.id,
                    source="proposed",
                    code=change.code or "",
                    name=change.name or "",
                    address=change.address or "",
                    latitude=change.latitude or 0,
                    longitude=change.longitude or 0,
                    status="proposed",
                    registered_voters=change.registered_voters or 0,
                )
            )
    return result
