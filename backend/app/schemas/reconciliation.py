import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReconcileRequest(BaseModel):
    election_id: uuid.UUID
    contest_id: uuid.UUID
    geography_node_id: uuid.UUID


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    tier: str
    engine_version: str
    input_hash: str
    output: dict
    missing_geography_ids: list[str]
    duration_ms: int
    created_at: datetime


class DiscrepancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field_name: str
    expected_value: int
    announced_value: int
    variance: int
    status: str
    assigned_to_id: uuid.UUID | None
    due_at: datetime | None
    resolution_category: str | None
    resolution_note: str | None


class DiscrepancyUpdate(BaseModel):
    status: Literal[
        "open", "assigned", "awaiting_clarification", "resolved", "unresolved", "further_review"
    ]
    assigned_to_id: uuid.UUID | None = None
    due_at: datetime | None = None
    resolution_category: str | None = Field(default=None, max_length=80)
    resolution_note: str | None = Field(default=None, max_length=2000)

    @field_validator("resolution_note")
    @classmethod
    def neutral_language(cls, value: str | None) -> str | None:
        if value and any(word in value.lower() for word in ("fraud", "criminal", "stolen")):
            raise ValueError("Use neutral factual language; criminal conclusions are not permitted")
        return value


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def neutral_language(cls, value: str) -> str:
        if any(word in value.lower() for word in ("fraud", "criminal", "stolen")):
            raise ValueError("Use neutral factual language")
        return value


class DashboardResponse(BaseModel):
    expected_polling_units: int
    submitted_ec8a: int
    missing_polling_unit_ids: list[uuid.UUID]
    submissions_by_form: dict[str, int]
    reconciliations_by_status: dict[str, int]
    investigations_by_status: dict[str, int]
    reconciliation_completion_rate: float
    average_reconciliation_latency_ms: float
