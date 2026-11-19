import json
from typing import Any

from geoalchemy2.functions import ST_GeomFromGeoJSON, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.geography import Ward
from app.models.scenarios import Scenario, ScenarioRevision


def point_geometry(latitude: float, longitude: float) -> Any:
    return ST_SetSRID(
        ST_GeomFromGeoJSON(json.dumps({"type": "Point", "coordinates": [longitude, latitude]})),
        4326,
    )


def ensure_revision(scenario: Scenario, expected: int) -> None:
    if scenario.revision != expected:
        raise AppError(
            code="scenario_revision_conflict",
            message="The scenario changed since it was loaded",
            status_code=409,
            details={"expected": expected, "current": scenario.revision},
        )


def ensure_point_in_scenario(
    db: Session, scenario: Scenario, latitude: float, longitude: float
) -> Any:
    point = point_geometry(latitude, longitude)
    is_inside = db.scalar(
        select(func.ST_Covers(Ward.boundary, point)).where(Ward.id == scenario.planning_ward_id)
    )
    if not is_inside:
        raise AppError(
            code="outside_planning_boundary",
            message="The proposed location is outside the scenario planning ward",
            status_code=422,
        )
    return point


def record_revision(
    db: Session, scenario: Scenario, actor_id, action: str, snapshot: dict[str, Any]
) -> None:
    scenario.revision += 1
    db.add(
        ScenarioRevision(
            scenario_id=scenario.id,
            revision=scenario.revision,
            action=action,
            snapshot=snapshot,
            actor_id=actor_id,
        )
    )
