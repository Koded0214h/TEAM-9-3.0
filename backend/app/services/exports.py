import csv
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reconciliation import Discrepancy, ReconciliationRun

LIMITATION = (
    "This report records arithmetic reconciliation of submitted records. "
    "It does not establish the physical authenticity of source documents or criminal conduct."
)


def export_payload(db: Session, workspace_id, election_id) -> tuple[bytes, bytes, dict]:
    runs = list(
        db.scalars(
            select(ReconciliationRun).where(
                ReconciliationRun.workspace_id == workspace_id,
                ReconciliationRun.election_id == election_id,
            )
        ).all()
    )
    discrepancies = list(
        db.scalars(select(Discrepancy).where(Discrepancy.workspace_id == workspace_id)).all()
    )
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["run_id", "tier", "geography_id", "status", "input_hash", "engine_version"])
    for run in runs:
        writer.writerow(
            [
                run.id,
                run.tier,
                run.geography_node_id,
                run.status,
                run.input_hash,
                run.engine_version,
            ]
        )
    csv_bytes = csv_buffer.getvalue().encode()
    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
    pdf.setTitle("TallyTrail Reconciliation Report")
    pdf.drawString(50, 800, "TallyTrail Reconciliation Report")
    pdf.drawString(50, 780, f"Generated: {datetime.now(UTC).isoformat()}")
    pdf.drawString(50, 760, f"Reconciliation runs: {len(runs)}")
    pdf.drawString(50, 740, f"Recorded discrepancies: {len(discrepancies)}")
    text = pdf.beginText(50, 700)
    for line in (LIMITATION[:95], LIMITATION[95:]):
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    pdf_bytes = pdf_buffer.getvalue()
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_id": str(workspace_id),
        "election_id": str(election_id),
        "engine_versions": sorted({run.engine_version for run in runs}),
        "files": {
            "reconciliation.csv": hashlib.sha256(csv_bytes).hexdigest(),
            "report.pdf": hashlib.sha256(pdf_bytes).hexdigest(),
        },
        "limitation": LIMITATION,
    }
    return csv_bytes, pdf_bytes, manifest


def build_export(
    db: Session, workspace_id, election_id, output_format: str
) -> tuple[bytes, str, str]:
    csv_bytes, pdf_bytes, manifest = export_payload(db, workspace_id, election_id)
    if output_format == "csv":
        return csv_bytes, "text/csv", "csv"
    if output_format == "pdf":
        return pdf_bytes, "application/pdf", "pdf"
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("reconciliation.csv", csv_bytes)
        archive.writestr("report.pdf", pdf_bytes)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return bundle.getvalue(), "application/zip", "zip"
