from app.core.celery import celery_app
from app.services.irev import fetch_public_record


@celery_app.task(
    name="irev.retrieve",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def retrieve_irev_task(external_reference: str) -> int:
    return len(fetch_public_record(external_reference))
