import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventListResponse

router = APIRouter(dependencies=[Depends(require_roles("system_admin"))])


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    actor_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    created_after: datetime | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AuditEventListResponse:
    filters = []
    if actor_id:
        filters.append(AuditEvent.actor_id == actor_id)
    if entity_type:
        filters.append(AuditEvent.entity_type == entity_type)
    if action:
        filters.append(AuditEvent.action == action)
    if created_after:
        filters.append(AuditEvent.created_at >= created_after)
    query = select(AuditEvent).where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)).all()
    )
    return AuditEventListResponse(items=items, total=total)
