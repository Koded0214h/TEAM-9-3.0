import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_Contains, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.models.geography import LGA, DatasetVersion, RegistrationArea, State, Ward
from app.schemas.geography import GeographyResponse, ResolvePointRequest, ResolvePointResponse

router = APIRouter()


def _active_filter(model: type[State] | type[LGA] | type[Ward] | type[RegistrationArea]):
    return model.dataset_id.in_(
        select(DatasetVersion.id).where(
            DatasetVersion.dataset_type == "administrative_geography",
            DatasetVersion.is_active.is_(True),
        )
    )


@router.get("/states", response_model=list[GeographyResponse])
def states(_: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[State]:
    return list(db.scalars(select(State).where(_active_filter(State)).order_by(State.name)).all())


@router.get("/lgas", response_model=list[GeographyResponse])
def lgas(state_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[LGA]:
    return list(db.scalars(select(LGA).where(LGA.state_id == state_id).order_by(LGA.name)).all())


@router.get("/wards", response_model=list[GeographyResponse])
def wards(lga_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[Ward]:
    return list(db.scalars(select(Ward).where(Ward.lga_id == lga_id).order_by(Ward.name)).all())


@router.get("/registration-areas", response_model=list[GeographyResponse])
def registration_areas(
    ward_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[RegistrationArea]:
    return list(
        db.scalars(
            select(RegistrationArea)
            .where(RegistrationArea.ward_id == ward_id)
            .order_by(RegistrationArea.name)
        ).all()
    )


@router.post("/resolve-point", response_model=ResolvePointResponse)
def resolve_point(
    payload: ResolvePointRequest, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ResolvePointResponse:
    point = ST_SetSRID(func.ST_MakePoint(payload.longitude, payload.latitude), 4326)
    return ResolvePointResponse(
        state=db.scalar(select(State).where(ST_Contains(State.boundary, point)).limit(1)),
        lga=db.scalar(select(LGA).where(ST_Contains(LGA.boundary, point)).limit(1)),
        ward=db.scalar(select(Ward).where(ST_Contains(Ward.boundary, point)).limit(1)),
        registration_area=db.scalar(
            select(RegistrationArea).where(ST_Contains(RegistrationArea.boundary, point)).limit(1)
        ),
    )
