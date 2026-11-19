import hashlib
import json
import time
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organisation import GeographyNode
from app.models.reconciliation import Discrepancy, ReconciliationRun
from app.models.results import ResultFigure, ResultSubmission

ENGINE_VERSION = "1.0.0"
TIER_CONFIG = {
    "ward": ("polling_unit", "EC8A", "EC8B"),
    "lga": ("ward", "EC8B", "EC8C"),
    "state": ("lga", "EC8C", "EC8D"),
}
TOTAL_FIELDS = (
    "valid_votes",
    "rejected_ballots",
    "total_votes_cast",
    "accredited_voters",
    "registered_voters",
)


def reconcile(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    election_id: uuid.UUID,
    contest_id: uuid.UUID,
    geography: GeographyNode,
    user_id: uuid.UUID,
) -> ReconciliationRun:
    started = time.perf_counter()
    child_level, lower_form, announced_form = TIER_CONFIG[geography.level]
    children = list(
        db.scalars(
            select(GeographyNode).where(
                GeographyNode.parent_id == geography.id,
                GeographyNode.level == child_level,
                GeographyNode.is_active.is_(True),
            )
        ).all()
    )
    child_ids = [item.id for item in children]
    lower = list(
        db.scalars(
            select(ResultSubmission).where(
                ResultSubmission.workspace_id == workspace_id,
                ResultSubmission.election_id == election_id,
                ResultSubmission.contest_id == contest_id,
                ResultSubmission.geography_node_id.in_(child_ids),
                ResultSubmission.form_type == lower_form,
                ResultSubmission.status.in_(("submitted", "verified")),
            )
        ).all()
    )
    by_geography = {item.geography_node_id: item for item in lower}
    missing = [str(item.id) for item in children if item.id not in by_geography]
    announced = db.scalar(
        select(ResultSubmission)
        .where(
            ResultSubmission.workspace_id == workspace_id,
            ResultSubmission.election_id == election_id,
            ResultSubmission.contest_id == contest_id,
            ResultSubmission.geography_node_id == geography.id,
            ResultSubmission.form_type == announced_form,
            ResultSubmission.status.in_(("submitted", "verified")),
        )
        .order_by(ResultSubmission.version.desc())
    )
    expected_totals = {
        field: sum((item.totals.get(field) or 0) for item in lower) for field in TOTAL_FIELDS
    }
    expected_candidates: dict[str, int] = defaultdict(int)
    if lower:
        figures = db.execute(
            select(ResultFigure.candidate_id, ResultFigure.votes).where(
                ResultFigure.submission_id.in_([item.id for item in lower])
            )
        ).all()
        for candidate_id, votes in figures:
            expected_candidates[str(candidate_id)] += votes
    announced_candidates = {}
    if announced:
        announced_candidates = {
            str(cid): votes
            for cid, votes in db.execute(
                select(ResultFigure.candidate_id, ResultFigure.votes).where(
                    ResultFigure.submission_id == announced.id
                )
            ).all()
        }
    snapshot = {
        "lower_submission_ids": sorted(str(item.id) for item in lower),
        "announced_submission_id": str(announced.id) if announced else None,
        "expected_totals": expected_totals,
        "expected_candidates": dict(sorted(expected_candidates.items())),
        "missing_geography_ids": sorted(missing),
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    comparisons = {}
    if announced:
        for field, expected in expected_totals.items():
            actual = announced.totals.get(field)
            if actual is not None:
                comparisons[field] = {
                    "expected": expected,
                    "announced": actual,
                    "variance": actual - expected,
                }
        for candidate_id, expected in expected_candidates.items():
            actual = announced_candidates.get(candidate_id, 0)
            comparisons[f"candidate:{candidate_id}"] = {
                "expected": expected,
                "announced": actual,
                "variance": actual - expected,
            }
    if not announced:
        status = "unverifiable"
    elif missing:
        status = "incomplete"
    elif any(item["variance"] for item in comparisons.values()):
        status = "discrepancy_detected"
    else:
        status = "matched"
    run = ReconciliationRun(
        workspace_id=workspace_id,
        election_id=election_id,
        contest_id=contest_id,
        geography_node_id=geography.id,
        announced_submission_id=announced.id if announced else None,
        status=status,
        tier=geography.level,
        engine_version=ENGINE_VERSION,
        input_hash=digest,
        input_snapshot=snapshot,
        output={"comparisons": comparisons},
        missing_geography_ids=missing,
        duration_ms=int((time.perf_counter() - started) * 1000),
        created_by_id=user_id,
    )
    db.add(run)
    db.flush()
    if status == "discrepancy_detected":
        for field, values in comparisons.items():
            if values["variance"]:
                candidate_id = (
                    uuid.UUID(field.split(":", 1)[1]) if field.startswith("candidate:") else None
                )
                db.add(
                    Discrepancy(
                        reconciliation_run_id=run.id,
                        workspace_id=workspace_id,
                        field_name=field,
                        candidate_id=candidate_id,
                        expected_value=values["expected"],
                        announced_value=values["announced"],
                        variance=values["variance"],
                    )
                )
    db.commit()
    db.refresh(run)
    return run
