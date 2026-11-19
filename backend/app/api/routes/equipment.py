import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.api.routes.scenarios import _scenario, effective_polling_units
from app.core.errors import AppError
from app.db.session import get_db
from app.models.equipment import (
    EquipmentOverride,
    EquipmentPlan,
    EquipmentPlanItem,
    EquipmentRuleVersion,
    EquipmentType,
    InventoryItem,
    InventorySnapshot,
)
from app.schemas.equipment import (
    EquipmentOverrideCreate,
    EquipmentOverrideResponse,
    EquipmentPlanResponse,
    EquipmentRuleCreate,
    EquipmentRuleResponse,
    EquipmentTypeCreate,
    EquipmentTypeResponse,
    InventoryCreate,
    InventoryResponse,
)
from app.services.equipment import allocate_stock, calculate_demand

router = APIRouter()
admin = Depends(require_roles("system_admin"))
operator = Depends(require_roles("operations_officer", "planning_admin", "system_admin"))


@router.get("/equipment-types", response_model=list[EquipmentTypeResponse])
def list_equipment_types(
    _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[EquipmentType]:
    return list(db.scalars(select(EquipmentType).order_by(EquipmentType.name)).all())


@router.post(
    "/equipment-types", response_model=EquipmentTypeResponse, status_code=201, dependencies=[admin]
)
def create_equipment_type(
    payload: EquipmentTypeCreate, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EquipmentType:
    item = EquipmentType(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/inventory-snapshots", response_model=InventoryResponse, status_code=201, dependencies=[admin]
)
def create_inventory(
    payload: InventoryCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> InventorySnapshot:
    snapshot = InventorySnapshot(
        ward_id=payload.ward_id,
        version=payload.version,
        source=payload.source,
        classification=payload.classification,
        created_by_id=user.id,
    )
    snapshot.items = [InventoryItem(**item.model_dump()) for item in payload.items]
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post(
    "/inventory-snapshots/{snapshot_id}/activate",
    response_model=InventoryResponse,
    dependencies=[admin],
)
def activate_inventory(
    snapshot_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> InventorySnapshot:
    snapshot = db.get(InventorySnapshot, snapshot_id)
    if snapshot is None:
        raise AppError(
            code="inventory_not_found", message="Inventory snapshot was not found", status_code=404
        )
    db.execute(
        update(InventorySnapshot)
        .where(InventorySnapshot.ward_id == snapshot.ward_id)
        .values(is_active=False)
    )
    snapshot.is_active = True
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/equipment-rules", response_model=list[EquipmentRuleResponse])
def list_equipment_rules(
    _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[EquipmentRuleVersion]:
    return list(
        db.scalars(
            select(EquipmentRuleVersion).order_by(EquipmentRuleVersion.created_at.desc())
        ).all()
    )


@router.post(
    "/equipment-rules", response_model=EquipmentRuleResponse, status_code=201, dependencies=[admin]
)
def create_equipment_rule(
    payload: EquipmentRuleCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EquipmentRuleVersion:
    rule = EquipmentRuleVersion(**payload.model_dump(), created_by_id=user.id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post(
    "/equipment-rules/{rule_id}/activate",
    response_model=EquipmentRuleResponse,
    dependencies=[admin],
)
def activate_equipment_rule(
    rule_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EquipmentRuleVersion:
    rule = db.get(EquipmentRuleVersion, rule_id)
    if rule is None:
        raise AppError(
            code="equipment_rule_not_found", message="Equipment rule was not found", status_code=404
        )
    same_ward = (
        EquipmentRuleVersion.ward_id == rule.ward_id
        if rule.ward_id
        else EquipmentRuleVersion.ward_id.is_(None)
    )
    db.execute(
        update(EquipmentRuleVersion)
        .where(EquipmentRuleVersion.equipment_type_id == rule.equipment_type_id, same_ward)
        .values(is_active=False)
    )
    rule.is_active = True
    db.commit()
    db.refresh(rule)
    return rule


@router.post(
    "/scenarios/{scenario_id}/equipment-plans",
    response_model=EquipmentPlanResponse,
    status_code=201,
    dependencies=[operator],
)
def create_equipment_plan(
    scenario_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EquipmentPlan:
    scenario = _scenario(db, scenario_id)
    inventory = db.scalar(
        select(InventorySnapshot).where(
            InventorySnapshot.ward_id == scenario.planning_ward_id,
            InventorySnapshot.is_active.is_(True),
        )
    )
    if inventory is None:
        raise AppError(
            code="inventory_unavailable",
            message="No active inventory applies to this scenario",
            status_code=409,
        )
    units = [
        unit for unit in effective_polling_units(scenario.id, user, db) if unit.status != "inactive"
    ]
    plan = EquipmentPlan(
        scenario_id=scenario.id,
        inventory_snapshot_id=inventory.id,
        input_snapshot={
            "scenario_revision": scenario.revision,
            "inventory_version": inventory.version,
            "inventory_classification": inventory.classification,
            "polling_units": [unit.model_dump(mode="json") for unit in units],
        },
        created_by_id=user.id,
    )
    db.add(plan)
    db.flush()
    for stock in inventory.items:
        rule = db.scalar(
            select(EquipmentRuleVersion)
            .where(
                EquipmentRuleVersion.equipment_type_id == stock.equipment_type_id,
                EquipmentRuleVersion.is_active.is_(True),
                or_(
                    EquipmentRuleVersion.ward_id == scenario.planning_ward_id,
                    EquipmentRuleVersion.ward_id.is_(None),
                ),
            )
            .order_by(EquipmentRuleVersion.ward_id.is_(None))
            .limit(1)
        )
        if rule is None:
            raise AppError(
                code="equipment_rule_unavailable",
                message=f"No active rule exists for equipment type {stock.equipment_type_id}",
                status_code=409,
            )
        demands = [
            (
                str(unit.id),
                calculate_demand(
                    unit.registered_voters,
                    fixed_minimum=rule.fixed_minimum,
                    voters_per_item=rule.voters_per_item,
                    maximum=rule.maximum_quantity,
                ),
                rule.priority,
            )
            for unit in units
        ]
        allocations = {
            allocation.polling_unit_id: allocation
            for allocation in allocate_stock(demands, stock.available_quantity)
        }
        for unit in units:
            allocation = allocations[str(unit.id)]
            db.add(
                EquipmentPlanItem(
                    plan_id=plan.id,
                    polling_unit_id=unit.id,
                    equipment_type_id=stock.equipment_type_id,
                    rule_id=rule.id,
                    voter_count=unit.registered_voters,
                    demanded_quantity=allocation.demand,
                    allocated_quantity=allocation.allocated,
                    shortage_quantity=max(allocation.demand - allocation.allocated, 0),
                    surplus_quantity=max(allocation.allocated - allocation.demand, 0),
                )
            )
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/equipment-plans/{plan_id}", response_model=EquipmentPlanResponse)
def get_equipment_plan(
    plan_id: uuid.UUID, _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EquipmentPlan:
    plan = db.get(EquipmentPlan, plan_id)
    if plan is None:
        raise AppError(
            code="equipment_plan_not_found", message="Equipment plan was not found", status_code=404
        )
    return plan


@router.post(
    "/equipment-plans/{plan_id}/items/{item_id}/override",
    response_model=EquipmentOverrideResponse,
    status_code=201,
    dependencies=[operator],
)
def override_equipment_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: EquipmentOverrideCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> EquipmentOverride:
    item = db.scalar(
        select(EquipmentPlanItem).where(
            EquipmentPlanItem.id == item_id, EquipmentPlanItem.plan_id == plan_id
        )
    )
    if item is None:
        raise AppError(
            code="equipment_plan_item_not_found",
            message="Equipment plan item was not found",
            status_code=404,
        )
    override = EquipmentOverride(
        plan_item_id=item.id,
        calculated_quantity=item.allocated_quantity,
        overridden_quantity=payload.quantity,
        reason=payload.reason,
        created_by_id=user.id,
    )
    item.allocated_quantity = payload.quantity
    item.shortage_quantity = max(item.demanded_quantity - payload.quantity, 0)
    item.surplus_quantity = max(payload.quantity - item.demanded_quantity, 0)
    db.add(override)
    db.commit()
    db.refresh(override)
    return override
