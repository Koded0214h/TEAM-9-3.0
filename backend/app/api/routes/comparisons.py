import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.capacity import effective_capacity_rule
from app.api.routes.scenarios import _scenario, effective_polling_units
from app.db.session import get_db
from app.models.allocation import AllocationRun
from app.models.equipment import EquipmentPlan
from app.models.geography import PollingUnit
from app.models.simulation import SimulationRun
from app.schemas.comparisons import (
    ChangeSummary,
    MetricValue,
    ScenarioComparisonResponse,
)
from app.services.capacity import classify_load

router = APIRouter()


@router.get("/scenarios/{scenario_id}/comparison", response_model=ScenarioComparisonResponse)
def compare_scenario(
    scenario_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioComparisonResponse:
    scenario = _scenario(db, scenario_id)
    baseline = list(
        db.scalars(
            select(PollingUnit).where(
                PollingUnit.dataset_id == scenario.baseline_polling_dataset_id,
                PollingUnit.ward_id == scenario.planning_ward_id,
            )
        ).all()
    )
    effective = effective_polling_units(scenario_id, user, db)
    effective_by_baseline = {
        unit.baseline_polling_unit_id: unit
        for unit in effective
        if unit.baseline_polling_unit_id is not None
    }
    rows = []
    relocated = deactivated = unchanged = 0
    for unit in baseline:
        current = effective_by_baseline[unit.id]
        if current.status == "inactive":
            change = "deactivated"
            deactivated += 1
        elif current.latitude != unit.latitude or current.longitude != unit.longitude:
            change = "relocated"
            relocated += 1
        else:
            change = "unchanged"
            unchanged += 1
        rows.append(
            {
                "polling_unit_id": str(unit.id),
                "code": unit.code,
                "change": change,
                "before": {
                    "latitude": unit.latitude,
                    "longitude": unit.longitude,
                    "voters": unit.registered_voters,
                    "status": unit.status,
                },
                "after": {
                    "latitude": current.latitude,
                    "longitude": current.longitude,
                    "voters": current.registered_voters,
                    "status": current.status,
                },
            }
        )
    proposed = [unit for unit in effective if unit.source == "proposed"]
    rows.extend(
        {
            "polling_unit_id": str(unit.id),
            "code": unit.code,
            "change": "added",
            "before": None,
            "after": unit.model_dump(mode="json"),
        }
        for unit in proposed
    )
    rule = effective_capacity_rule(db, scenario.planning_ward_id)
    baseline_overloaded = sum(
        classify_load(
            unit.registered_voters,
            target=rule.target_voters,
            maximum=rule.maximum_voters,
            underutilized_ratio=rule.underutilized_ratio,
        ).label
        == "overloaded"
        for unit in baseline
    )
    scenario_overloaded = sum(
        classify_load(
            unit.registered_voters,
            target=rule.target_voters,
            maximum=rule.maximum_voters,
            underutilized_ratio=rule.underutilized_ratio,
        ).label
        == "overloaded"
        for unit in effective
        if unit.status != "inactive"
    )
    metrics = {
        "over_capacity_polling_units": MetricValue(
            status="available",
            baseline=baseline_overloaded,
            scenario=scenario_overloaded,
            delta=scenario_overloaded - baseline_overloaded,
            unit="polling_units",
            explanation=f"Calculated with capacity rule {rule.version}.",
        )
    }
    warnings = []
    allocation = db.scalar(
        select(AllocationRun).where(
            AllocationRun.scenario_id == scenario.id, AllocationRun.is_selected.is_(True)
        )
    )
    if allocation and allocation.status == "succeeded":
        values = (allocation.result or {}).get("objective_values", {})
        metrics["estimated_travel_distance"] = MetricValue(
            status="available",
            scenario=values.get("travel_distance"),
            unit="engine_defined",
            explanation="Supplied by the selected allocation engine result.",
        )
    else:
        metrics["estimated_travel_distance"] = MetricValue(
            status="unavailable",
            explanation="No successful selected allocation run exists; no value was fabricated.",
        )
    plan = db.scalar(
        select(EquipmentPlan)
        .where(EquipmentPlan.scenario_id == scenario.id)
        .order_by(EquipmentPlan.created_at.desc())
        .limit(1)
    )
    if plan:
        met = sum(item.shortage_quantity == 0 for item in plan.items)
        coverage = round(met / len(plan.items) * 100, 2) if plan.items else 100.0
        metrics["equipment_coverage"] = MetricValue(
            status="available",
            scenario=coverage,
            unit="percent",
            explanation="Share of equipment-plan items with no shortage.",
        )
    else:
        metrics["equipment_coverage"] = MetricValue(
            status="unavailable", explanation="No equipment plan exists."
        )
    simulation = db.scalar(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id, SimulationRun.status == "succeeded")
        .order_by(SimulationRun.created_at.desc())
        .limit(1)
    )
    if simulation:
        metrics["estimated_queue_time"] = MetricValue(
            status="available",
            scenario=(simulation.result or {}).get("average_wait_minutes"),
            unit="minutes",
            explanation="Supplied by the latest successful simulation run.",
        )
    else:
        metrics["estimated_queue_time"] = MetricValue(
            status="unavailable",
            explanation="No successful simulation exists; no estimate was fabricated.",
        )
    return ScenarioComparisonResponse(
        scenario_id=scenario.id,
        scenario_revision=scenario.revision,
        baseline_polling_dataset_id=scenario.baseline_polling_dataset_id,
        baseline_geography_dataset_id=scenario.baseline_geography_dataset_id,
        compatible=True,
        changes=ChangeSummary(
            added=len(proposed),
            relocated=relocated,
            deactivated=deactivated,
            unchanged=unchanged,
        ),
        polling_units=rows,
        metrics=metrics,
        explanations=[
            "Official baseline records remain unchanged; scenario changes are overlays.",
            f"Capacity classifications use rule version {rule.version}.",
        ],
        warnings=warnings,
    )
