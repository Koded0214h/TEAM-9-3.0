import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str | None
    actor_id: uuid.UUID | None
    metadata_json: dict
    previous_hash: str
    event_hash: str
    created_at: datetime


class LegalHoldCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


class IReVRecordCreate(BaseModel):
    geography_node_id: uuid.UUID
    document_id: uuid.UUID
    external_reference: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl | None = None
    response_metadata: dict = Field(default_factory=dict)


class ExportCreate(BaseModel):
    election_id: uuid.UUID
    geography_node_id: uuid.UUID | None = None
    format: Literal["csv", "pdf", "zip"] = "zip"


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    progress: int
    format: str
    manifest_sha256: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
