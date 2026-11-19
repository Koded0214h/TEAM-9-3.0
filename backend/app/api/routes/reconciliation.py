import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_workspace_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.organisation import GeographyNode, Membership
from app.models.reconciliation import (
    Discrepancy,
    DiscrepancyComment,
    DiscrepancyStatusHistory,
    ReconciliationRun,
)
from app.models.results import ResultSubmission
from app.schemas.reconciliation import (
    CommentCreate,
    DashboardResponse,
    DiscrepancyResponse,
    DiscrepancyUpdate,
    ReconcileRequest,
    ReconciliationResponse,
)
from app.services.reconciliation import TIER_CONFIG, reconcile
from app.tasks.reconciliation import run_reconciliation_task

router = APIRouter(prefix="/workspaces/{workspace_id}")
operators = require_workspace_roles(
    "party_admin", "operations", "collation_officer", require_mfa=True
)
reviewers = require_workspace_roles(
    "party_admin", "operations", "legal_compliance", require_mfa=True
)


@router.post("/reconciliations", response_model=ReconciliationResponse, status_code=201)
def run_reconciliation(
    workspace_id: uuid.UUID,
    payload: ReconcileRequest,
    user: CurrentUser,
    _: Annotated[Membership, Depends(operators)],
    db: Annotated[Session, Depends(get_db)],
) -> ReconciliationRun:
    node = db.get(GeographyNode, payload.geography_node_id)
    if node is None or node.workspace_id != workspace_id or node.level not in TIER_CONFIG:
        raise AppError(
            "invalid_reconciliation_geography",
            "Reconciliation requires a workspace ward, LGA, or state",
            422,
        )
    return reconcile(
        db,
        workspace_id=workspace_id,
        election_id=payload.election_id,
        contest_id=payload.contest_id,
        geography=node,
        user_id=user.id,
    )


@router.post("/reconciliations/jobs", status_code=202)
def queue_reconciliation(
    workspace_id: uuid.UUID,
    payload: ReconcileRequest,
    user: CurrentUser,
    _: Annotated[Membership, Depends(operators)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    node = db.get(GeographyNode, payload.geography_node_id)
    if node is None or node.workspace_id != workspace_id or node.level not in ("lga", "state"):
        raise AppError(
            "invalid_background_tier", "Background reconciliation supports LGA and state", 422
        )
    task = run_reconciliation_task.delay(
        str(workspace_id),
        str(payload.election_id),
        str(payload.contest_id),
        str(node.id),
        str(user.id),
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/reconciliations", response_model=list[ReconciliationResponse])
def list_reconciliations(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(reviewers)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReconciliationRun]:
    return list(
        db.scalars(
            select(ReconciliationRun)
            .where(ReconciliationRun.workspace_id == workspace_id)
            .order_by(ReconciliationRun.created_at.desc())
        ).all()
    )


@router.get("/discrepancies", response_model=list[DiscrepancyResponse])
def list_discrepancies(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(reviewers)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
) -> list[Discrepancy]:
    query = select(Discrepancy).where(Discrepancy.workspace_id == workspace_id)
    if status:
        query = query.where(Discrepancy.status == status)
    return list(db.scalars(query.order_by(Discrepancy.created_at.desc())).all())


@router.patch("/discrepancies/{discrepancy_id}", response_model=DiscrepancyResponse)
def update_discrepancy(
    workspace_id: uuid.UUID,
    discrepancy_id: uuid.UUID,
    payload: DiscrepancyUpdate,
    user: CurrentUser,
    _: Annotated[Membership, Depends(reviewers)],
    db: Annotated[Session, Depends(get_db)],
) -> Discrepancy:
    item = db.get(Discrepancy, discrepancy_id)
    if item is None or item.workspace_id != workspace_id:
        raise AppError("discrepancy_not_found", "Discrepancy was not found", 404)
    old = item.status
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    if old != item.status:
        db.add(
            DiscrepancyStatusHistory(
                discrepancy_id=item.id,
                from_status=old,
                to_status=item.status,
                changed_by_id=user.id,
            )
        )
    db.commit()
    db.refresh(item)
    return item


@router.post("/discrepancies/{discrepancy_id}/comments", status_code=201)
def add_comment(
    workspace_id: uuid.UUID,
    discrepancy_id: uuid.UUID,
    payload: CommentCreate,
    user: CurrentUser,
    _: Annotated[Membership, Depends(reviewers)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    item = db.get(Discrepancy, discrepancy_id)
    if item is None or item.workspace_id != workspace_id:
        raise AppError("discrepancy_not_found", "Discrepancy was not found", 404)
    comment = DiscrepancyComment(discrepancy_id=item.id, author_id=user.id, body=payload.body)
    db.add(comment)
    db.commit()
    return {"id": comment.id, "created": True}


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(reviewers)],
    db: Annotated[Session, Depends(get_db)],
    election_id: uuid.UUID,
) -> DashboardResponse:
    polling_ids = set(
        db.scalars(
            select(GeographyNode.id).where(
                GeographyNode.workspace_id == workspace_id,
                GeographyNode.level == "polling_unit",
                GeographyNode.is_active.is_(True),
            )
        ).all()
    )
    rows = db.execute(
        select(ResultSubmission.form_type, func.count())
        .where(
            ResultSubmission.workspace_id == workspace_id,
            ResultSubmission.election_id == election_id,
            ResultSubmission.status.in_(("submitted", "verified")),
        )
        .group_by(ResultSubmission.form_type)
    ).all()
    forms = dict(rows)
    submitted_pu = set(
        db.scalars(
            select(ResultSubmission.geography_node_id).where(
                ResultSubmission.workspace_id == workspace_id,
                ResultSubmission.election_id == election_id,
                ResultSubmission.form_type == "EC8A",
                ResultSubmission.status.in_(("submitted", "verified")),
            )
        ).all()
    )
    rec_rows = db.execute(
        select(ReconciliationRun.status, func.count())
        .where(
            ReconciliationRun.workspace_id == workspace_id,
            ReconciliationRun.election_id == election_id,
        )
        .group_by(ReconciliationRun.status)
    ).all()
    inv_rows = db.execute(
        select(Discrepancy.status, func.count())
        .where(Discrepancy.workspace_id == workspace_id)
        .group_by(Discrepancy.status)
    ).all()
    recs = dict(rec_rows)
    rec_total = sum(recs.values())
    completed = recs.get("matched", 0) + recs.get("discrepancy_detected", 0)
    latency = (
        db.scalar(
            select(func.avg(ReconciliationRun.duration_ms)).where(
                ReconciliationRun.workspace_id == workspace_id,
                ReconciliationRun.election_id == election_id,
            )
        )
        or 0
    )
    return DashboardResponse(
        expected_polling_units=len(polling_ids),
        submitted_ec8a=len(submitted_pu),
        missing_polling_unit_ids=sorted(polling_ids - submitted_pu, key=str),
        submissions_by_form={key: forms.get(key, 0) for key in ("EC8A", "EC8B", "EC8C", "EC8D")},
        reconciliations_by_status=recs,
        investigations_by_status=dict(inv_rows),
        reconciliation_completion_rate=round(completed / rec_total * 100, 2) if rec_total else 0,
        average_reconciliation_latency_ms=float(latency),
    )
