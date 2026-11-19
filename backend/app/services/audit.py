import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import AuditEvent

GENESIS_HASH = "0" * 64
SECRET_KEYS = {"password", "token", "secret", "api_key", "document_bytes"}


def safe_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    return {
        key: item
        for key, item in (value or {}).items()
        if not any(word in key.lower() for word in SECRET_KEYS)
    }


def append_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    workspace_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    metadata: dict[str, Any] | None = None,
    effective_role: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    previous = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == workspace_id)
        .order_by(AuditEvent.created_at.desc())
        .with_for_update()
    )
    previous_hash = previous.event_hash if previous else GENESIS_HASH
    payload = {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "workspace_id": str(workspace_id) if workspace_id else None,
        "actor_id": str(actor_id) if actor_id else None,
        "metadata": safe_metadata(metadata),
        "previous_hash": previous_hash,
    }
    event_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    event = AuditEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        effective_role=effective_role,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=payload["metadata"],
        previous_hash=previous_hash,
        event_hash=event_hash,
    )
    db.add(event)
    return event


def verify_chain(events: list[AuditEvent]) -> bool:
    previous_hash = GENESIS_HASH
    for event in events:
        payload = {
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "workspace_id": str(event.workspace_id) if event.workspace_id else None,
            "actor_id": str(event.actor_id) if event.actor_id else None,
            "metadata": event.metadata_json,
            "previous_hash": previous_hash,
        }
        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if event.previous_hash != previous_hash or event.event_hash != expected:
            return False
        previous_hash = event.event_hash
    return True
