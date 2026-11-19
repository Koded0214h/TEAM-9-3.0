import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_workspace_roles
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.compliance import AuditEvent, ExportJob, IReVRecord, LegalHold
from app.models.organisation import GeographyNode, Membership
from app.models.results import Document
from app.schemas.compliance import (
    AuditEventResponse,
    ExportCreate,
    ExportResponse,
    IReVRecordCreate,
    LegalHoldCreate,
)
from app.schemas.results import DocumentAccessResponse
from app.services.audit import append_audit, verify_chain
from app.services.cloudinary_storage import signed_download_url
from app.tasks.exports import generate_export_task

router = APIRouter(prefix="/workspaces/{workspace_id}")
compliance = require_workspace_roles("party_admin", "legal_compliance", require_mfa=True)
operations = require_workspace_roles("party_admin", "operations", require_mfa=True)


@router.get("/audit", response_model=list[AuditEventResponse])
def search_audit(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(AuditEvent.workspace_id == workspace_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    return list(
        db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(min(limit, 500))).all()
    )


@router.get("/audit/verify")
def verify_audit(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace_id)
            .order_by(AuditEvent.created_at)
        ).all()
    )
    return {"valid": verify_chain(events), "event_count": len(events)}


@router.post("/legal-holds", status_code=201)
def create_legal_hold(
    workspace_id: uuid.UUID,
    payload: LegalHoldCreate,
    request: Request,
    user: CurrentUser,
    membership: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    hold = LegalHold(workspace_id=workspace_id, created_by_id=user.id, **payload.model_dump())
    db.add(hold)
    append_audit(
        db,
        action="legal_hold.created",
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        workspace_id=workspace_id,
        actor_id=user.id,
        effective_role=membership.role,
        request_id=getattr(request.state, "request_id", None),
        metadata={"reason": payload.reason},
    )
    db.commit()
    return {"id": hold.id, "active": True}


@router.post("/irev/records", status_code=201)
def register_irev_record(
    workspace_id: uuid.UUID,
    payload: IReVRecordCreate,
    request: Request,
    user: CurrentUser,
    membership: Annotated[Membership, Depends(operations)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    document = db.get(Document, payload.document_id)
    node = db.get(GeographyNode, payload.geography_node_id)
    if (
        document is None
        or document.workspace_id != workspace_id
        or document.provenance != "public_irev"
        or node is None
        or node.workspace_id != workspace_id
    ):
        raise AppError(
            "invalid_irev_record",
            "A public-IReV document and workspace geography are required",
            422,
        )
    record = IReVRecord(
        workspace_id=workspace_id,
        source_url=str(payload.source_url) if payload.source_url else None,
        **payload.model_dump(exclude={"source_url"}),
    )
    db.add(record)
    append_audit(
        db,
        action="irev_record.registered",
        entity_type="irev_record",
        entity_id=str(record.id),
        workspace_id=workspace_id,
        actor_id=user.id,
        effective_role=membership.role,
        request_id=getattr(request.state, "request_id", None),
        metadata={"external_reference": payload.external_reference},
    )
    db.commit()
    return {
        "id": record.id,
        "provenance": "public_irev",
        "provider_ingestion_enabled": get_settings().irev_enabled,
    }


@router.post("/exports", response_model=ExportResponse, status_code=202)
def create_export(
    workspace_id: uuid.UUID,
    payload: ExportCreate,
    request: Request,
    user: CurrentUser,
    membership: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportJob:
    job = ExportJob(workspace_id=workspace_id, requested_by_id=user.id, **payload.model_dump())
    db.add(job)
    db.flush()
    append_audit(
        db,
        action="export.queued",
        entity_type="export_job",
        entity_id=str(job.id),
        workspace_id=workspace_id,
        actor_id=user.id,
        effective_role=membership.role,
        request_id=getattr(request.state, "request_id", None),
        metadata={"format": job.format},
    )
    db.commit()
    generate_export_task.delay(str(job.id))
    db.refresh(job)
    return job


@router.get("/exports/{job_id}", response_model=ExportResponse)
def get_export(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    _: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportJob:
    job = db.get(ExportJob, job_id)
    if job is None or job.workspace_id != workspace_id:
        raise AppError("export_not_found", "Export was not found", 404)
    return job


@router.get("/exports/{job_id}/access", response_model=DocumentAccessResponse)
def access_export(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    _: Annotated[Membership, Depends(compliance)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentAccessResponse:
    job = db.get(ExportJob, job_id)
    if job is None or job.workspace_id != workspace_id or job.status != "completed":
        raise AppError("export_unavailable", "Completed export was not found", 404)
    return DocumentAccessResponse(
        url=signed_download_url(job.cloudinary_public_id, job.resource_type, job.cloudinary_format),
        expires_in=3600,
    )
