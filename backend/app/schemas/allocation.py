import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AllocationRunCreate(BaseModel):
    objective_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "load_balance": 1.0,
            "travel_distance": 1.0,
            "changed_assignments": 0.5,
        }
    )
    constraints: dict[str, Any] = Field(default_factory=dict)


class AllocationItem(BaseModel):
    polling_unit_id: uuid.UUID
    before_voters: int = Field(ge=0)
    after_voters: int = Field(ge=0)
    estimated_distance_delta_km: float | None = None


class AllocationEngineResult(BaseModel):
    status: Literal["succeeded", "not_implemented", "failed"]
    allocations: list[AllocationItem] = Field(default_factory=list)
    objective_values: dict[str, float] = Field(default_factory=dict)
    satisfied_constraints: list[str] = Field(default_factory=list)
    unsatisfied_constraints: list[str] = Field(default_factory=list)
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class AllocationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scenario_id: uuid.UUID
    status: str
    progress_stage: str
    engine_name: str
    engine_version: str
    contract_version: str
    input_snapshot: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    is_selected: bool
    created_by_id: uuid.UUID
    created_at: datetime
    completed_at: datetime | None
