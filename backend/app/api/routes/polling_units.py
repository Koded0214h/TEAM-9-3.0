import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.errors import AppError
from app.db.session import get_db
from app.models.geography import DatasetVersion, PollingUnit, Ward
from app.schemas.geography import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    PollingUnitListResponse,
    PollingUnitResponse,
)

router = APIRouter()


def _active_units():
    return select(PollingUnit).join(DatasetVersion).where(DatasetVersion.is_active.is_(True))


@router.get("", response_model=PollingUnitListResponse)
def list_polling_units(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    ward_id: uuid.UUID | None = None,
    lga_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PollingUnitListResponse:
    query = _active_units()
    if ward_id:
        query = query.where(PollingUnit.ward_id == ward_id)
    if lga_id:
        query = query.join(Ward).where(Ward.lga_id == lga_id)
    if status:
        query = query.where(PollingUnit.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                PollingUnit.code.ilike(term),
                PollingUnit.name.ilike(term),
                PollingUnit.address.ilike(term),
            )
        )
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    items = list(db.scalars(query.order_by(PollingUnit.code).offset(offset).limit(limit)).all())
    classification = (
        db.scalar(
            select(DatasetVersion.classification).where(
                DatasetVersion.is_active.is_(True), DatasetVersion.dataset_type == "polling_units"
            )
        )
        or "unknown"
    )
    return PollingUnitListResponse(
        items=items, total=db.scalar(count_query) or 0, dataset_classification=classification
    )


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
def polling_units_geojson(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    ward_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> GeoJSONFeatureCollection:
    query = _active_units()
    if ward_id:
        query = query.where(PollingUnit.ward_id == ward_id)
    units = list(db.scalars(query.limit(limit)).all())
    return GeoJSONFeatureCollection(
        features=[
            GeoJSONFeature(
                geometry={"type": "Point", "coordinates": [unit.longitude, unit.latitude]},
                properties={
                    "id": str(unit.id),
                    "code": unit.code,
                    "name": unit.name,
                    "status": unit.status,
                    "registered_voters": unit.registered_voters,
                },
            )
            for unit in units
        ]
    )


@router.get("/{unit_id}", response_model=PollingUnitResponse)
def get_polling_unit(
    unit_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> PollingUnit:
    unit = db.get(PollingUnit, unit_id)
    if unit is None:
        raise AppError(
            code="polling_unit_not_found", message="Polling unit was not found", status_code=404
        )
    return unit


@router.get("/{unit_id}/nearby", response_model=list[PollingUnitResponse])
def nearby_polling_units(
    unit_id: uuid.UUID,
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    radius_meters: Annotated[int, Query(ge=100, le=100000)] = 5000,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[PollingUnit]:
    unit = db.get(PollingUnit, unit_id)
    if unit is None:
        raise AppError(
            code="polling_unit_not_found", message="Polling unit was not found", status_code=404
        )
    distance = func.ST_DistanceSphere(PollingUnit.location, unit.location)
    query = (
        select(PollingUnit)
        .where(
            PollingUnit.id != unit.id,
            ST_DWithin(
                PollingUnit.location.cast(Geography),
                unit.location.cast(Geography),
                radius_meters,
            ),
        )
        .order_by(distance)
        .limit(limit)
    )
    return list(db.scalars(query).all())
