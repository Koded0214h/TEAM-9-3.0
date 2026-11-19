import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from geoalchemy2.functions import ST_GeomFromGeoJSON, ST_Multi, ST_SetSRID
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.geography import (
    LGA,
    DatasetVersion,
    ImportJob,
    PollingUnit,
    RegistrationArea,
    State,
    Ward,
)
from app.schemas.geography import DatasetCreate, DatasetResponse, ImportResponse
from app.services.imports import validate_geojson, validate_polling_unit_csv

router = APIRouter()


def _geometry(value: dict) -> object:
    return ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(json.dumps(value)), 4326))


def _ingest_administrative_geography(
    db: Session, dataset: DatasetVersion, features: list[dict]
) -> None:
    grouped = {
        level: [f for f in features if f["properties"]["level"] == level]
        for level in ("state", "lga", "ward", "registration_area")
    }
    parents: dict[str, dict[str, object]] = {level: {} for level in grouped}
    for feature in grouped["state"]:
        props = feature["properties"]
        entity = State(
            dataset_id=dataset.id,
            code=props["code"],
            name=props["name"],
            boundary=_geometry(feature["geometry"]),
        )
        db.add(entity)
        parents["state"][props["code"]] = entity
    db.flush()
    hierarchy = (("lga", LGA, "state", "state_id"), ("ward", Ward, "lga", "lga_id"))
    for level, model, parent_level, foreign_key in hierarchy:
        for feature in grouped[level]:
            props = feature["properties"]
            entity = model(
                dataset_id=dataset.id,
                code=props["code"],
                name=props["name"],
                boundary=_geometry(feature["geometry"]),
                **{foreign_key: parents[parent_level][props["parent_code"]].id},
            )
            db.add(entity)
            parents[level][props["code"]] = entity
        db.flush()
    for feature in grouped["registration_area"]:
        props = feature["properties"]
        db.add(
            RegistrationArea(
                dataset_id=dataset.id,
                ward_id=parents["ward"][props["parent_code"]].id,
                code=props["code"],
                name=props["name"],
                boundary=_geometry(feature["geometry"]),
            )
        )


@router.get("", response_model=list[DatasetResponse])
def list_datasets(_: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[DatasetVersion]:
    return list(db.scalars(select(DatasetVersion).order_by(DatasetVersion.created_at.desc())).all())


@router.post("", response_model=DatasetResponse, status_code=201)
def create_dataset(
    payload: DatasetCreate,
    user: Annotated[object, Depends(require_roles("system_admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> DatasetVersion:
    dataset = DatasetVersion(**payload.model_dump(), uploaded_by_id=user.id)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> DatasetVersion:
    dataset = db.get(DatasetVersion, dataset_id)
    if dataset is None:
        raise AppError(code="dataset_not_found", message="Dataset was not found", status_code=404)
    return dataset


@router.post("/{dataset_id}/imports", response_model=ImportResponse)
async def import_dataset(
    dataset_id: uuid.UUID,
    _: Annotated[object, Depends(require_roles("system_admin"))],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    dry_run: Annotated[bool, Query()] = False,
) -> ImportJob:
    dataset = db.get(DatasetVersion, dataset_id)
    if dataset is None:
        raise AppError(code="dataset_not_found", message="Dataset was not found", status_code=404)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise AppError(
            code="file_too_large", message="Import files may not exceed 25 MB", status_code=413
        )
    if dataset.dataset_type == "polling_units":
        result = validate_polling_unit_csv(content)
    elif dataset.dataset_type in {"administrative_geography", "geospatial_context"}:
        result = validate_geojson(
            content, administrative=dataset.dataset_type == "administrative_geography"
        )
    else:
        raise AppError(
            code="unsupported_import",
            message="This dataset type has no importer yet",
            status_code=422,
        )
    ward_by_code: dict[str, Ward] = {}
    if dataset.dataset_type == "polling_units" and not result.errors:
        ward_codes = {row["ward_code"] for row in result.rows}
        wards = db.scalars(
            select(Ward)
            .join(DatasetVersion)
            .where(
                DatasetVersion.dataset_type == "administrative_geography",
                DatasetVersion.is_active.is_(True),
                Ward.code.in_(ward_codes),
            )
        ).all()
        ward_by_code = {ward.code: ward for ward in wards}
        for row in result.rows:
            if row["ward_code"] not in ward_by_code:
                result.errors.append(
                    {"code": row["code"], "message": f"Unknown ward_code: {row['ward_code']}"}
                )
    job = ImportJob(
        dataset_id=dataset.id,
        filename=file.filename or "upload",
        status="validated" if dry_run else ("failed" if result.errors else "succeeded"),
        total_rows=len(result.rows) + len(result.errors),
        valid_rows=len(result.rows),
        invalid_rows=len(result.errors),
        errors=result.errors,
        completed_at=datetime.now(UTC),
    )
    db.add(job)
    if not dry_run and not result.errors and dataset.dataset_type == "administrative_geography":
        _ingest_administrative_geography(db, dataset, result.rows)
    if not dry_run and not result.errors and dataset.dataset_type == "polling_units":
        for row in result.rows:
            ward = ward_by_code[row["ward_code"]]
            latitude, longitude = float(row["latitude"]), float(row["longitude"])
            db.add(
                PollingUnit(
                    dataset_id=dataset.id,
                    ward_id=ward.id,
                    code=row["code"].strip(),
                    name=row["name"].strip(),
                    address=row["address"].strip(),
                    latitude=latitude,
                    longitude=longitude,
                    coordinate_source=(row.get("coordinate_source") or "imported").strip(),
                    registered_voters=int(row["registered_voters"]),
                    location=ST_SetSRID(
                        ST_GeomFromGeoJSON(
                            json.dumps({"type": "Point", "coordinates": [longitude, latitude]})
                        ),
                        4326,
                    ),
                )
            )
    dataset.checksum = result.checksum
    dataset.row_count = len(result.rows)
    dataset.status = job.status
    db.commit()
    db.refresh(job)
    return job


@router.post("/{dataset_id}/activate", response_model=DatasetResponse)
def activate_dataset(
    dataset_id: uuid.UUID,
    _: Annotated[object, Depends(require_roles("system_admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> DatasetVersion:
    dataset = db.get(DatasetVersion, dataset_id)
    if dataset is None:
        raise AppError(code="dataset_not_found", message="Dataset was not found", status_code=404)
    if dataset.status != "succeeded":
        raise AppError(
            code="dataset_not_ready",
            message="Only successfully imported datasets can be activated",
            status_code=409,
        )
    db.execute(
        update(DatasetVersion)
        .where(DatasetVersion.dataset_type == dataset.dataset_type)
        .values(is_active=False)
    )
    dataset.is_active = True
    dataset.status = "active"
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}/imports/{import_id}", response_model=ImportResponse)
def get_import(
    dataset_id: uuid.UUID,
    import_id: uuid.UUID,
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ImportJob:
    job = db.scalar(
        select(ImportJob).where(ImportJob.id == import_id, ImportJob.dataset_id == dataset_id)
    )
    if job is None:
        raise AppError(code="import_not_found", message="Import job was not found", status_code=404)
    return job
