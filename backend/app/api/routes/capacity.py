import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.capacity import CapacityRuleVersion
from app.schemas.capacity import CapacityRuleCreate, CapacityRuleResponse

router = APIRouter()


@router.get("", response_model=list[CapacityRuleResponse])
def list_capacity_rules(
    _: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[CapacityRuleVersion]:
    return list(
        db.scalars(
            select(CapacityRuleVersion).order_by(CapacityRuleVersion.created_at.desc())
        ).all()
    )


@router.post("", response_model=CapacityRuleResponse, status_code=201)
def create_capacity_rule(
    payload: CapacityRuleCreate,
    _: Annotated[object, Depends(require_roles("system_admin"))],
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CapacityRuleVersion:
    rule = CapacityRuleVersion(**payload.model_dump(), created_by_id=user.id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/{rule_id}/activate", response_model=CapacityRuleResponse)
def activate_capacity_rule(
    rule_id: uuid.UUID,
    _: Annotated[object, Depends(require_roles("system_admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> CapacityRuleVersion:
    rule = db.get(CapacityRuleVersion, rule_id)
    if rule is None:
        raise AppError(
            code="capacity_rule_not_found", message="Capacity rule was not found", status_code=404
        )
    same_scope = (
        CapacityRuleVersion.ward_id == rule.ward_id
        if rule.ward_id
        else CapacityRuleVersion.ward_id.is_(None)
    )
    db.execute(update(CapacityRuleVersion).where(same_scope).values(is_active=False))
    rule.is_active = True
    db.commit()
    db.refresh(rule)
    return rule


def effective_capacity_rule(db: Session, ward_id: uuid.UUID) -> CapacityRuleVersion:
    rule = db.scalar(
        select(CapacityRuleVersion)
        .where(
            CapacityRuleVersion.is_active.is_(True),
            or_(CapacityRuleVersion.ward_id == ward_id, CapacityRuleVersion.ward_id.is_(None)),
        )
        .order_by(CapacityRuleVersion.ward_id.is_(None))
        .limit(1)
    )
    if rule is None:
        raise AppError(
            code="capacity_rule_unavailable",
            message="No active capacity rule applies to this ward",
            status_code=409,
        )
    return rule
