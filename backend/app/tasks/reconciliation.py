import uuid

from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.models.organisation import GeographyNode
from app.services.reconciliation import reconcile


@celery_app.task(
    name="reconciliation.run",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_reconciliation_task(
    workspace_id: str,
    election_id: str,
    contest_id: str,
    geography_node_id: str,
    user_id: str,
) -> str:
    with SessionLocal() as db:
        node = db.get(GeographyNode, uuid.UUID(geography_node_id))
        run = reconcile(
            db,
            workspace_id=uuid.UUID(workspace_id),
            election_id=uuid.UUID(election_id),
            contest_id=uuid.UUID(contest_id),
            geography=node,
            user_id=uuid.UUID(user_id),
        )
        return str(run.id)
