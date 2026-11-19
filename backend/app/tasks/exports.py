import hashlib
import uuid
from datetime import UTC, datetime

from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.models.compliance import ExportJob
from app.services.cloudinary_storage import upload_evidence
from app.services.exports import build_export


@celery_app.task(
    name="exports.generate",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def generate_export_task(job_id: str) -> str:
    with SessionLocal() as db:
        job = db.get(ExportJob, uuid.UUID(job_id))
        job.status, job.progress = "processing", 10
        db.commit()
        try:
            content, media_type, extension = build_export(
                db, job.workspace_id, job.election_id, job.format
            )
            job.progress = 75
            uploaded = upload_evidence(
                content, f"tallytrail-export-{job.id}.{extension}", media_type, job.workspace_id
            )
            job.cloudinary_public_id = uploaded["public_id"]
            job.cloudinary_format = uploaded.get("format") or extension
            job.resource_type = uploaded["resource_type"]
            job.manifest_sha256 = hashlib.sha256(content).hexdigest()
            job.status, job.progress, job.completed_at = "completed", 100, datetime.now(UTC)
        except Exception as exc:
            job.status, job.error_message = "failed", str(exc)[:1000]
        db.commit()
        return str(job.id)
