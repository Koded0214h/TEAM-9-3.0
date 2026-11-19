import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulationAssumptionCreate(BaseModel):
    ward_id: uuid.UUID | None = None
    version: str = Field(min_length=1, max_length=80)
    voting_period_minutes: int = Field(gt=0, le=1440)
    arrival_pattern: dict[str, Any]
    average_service_minutes: float = Field(gt=0)
    default_staff_count: int = Field(gt=0)
    equipment_uptime_ratio: float = Field(gt=0, le=1)
    explanation: str = Field(min_length=3, max_length=500)


class SimulationAssumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ward_id: uuid.UUID | None
    version: str
    voting_period_minutes: int
    arrival_pattern: dict[str, Any]
    average_service_minutes: float
    default_staff_count: int
    equipment_uptime_ratio: float
    is_active: bool
    explanation: str


class SimulationRunCreate(BaseModel):
    equipment_plan_id: uuid.UUID | None = None


class PollingUnitSimulationResult(BaseModel):
    polling_unit_id: uuid.UUID
    peak_queue: int = Field(ge=0)
    average_wait_minutes: float = Field(ge=0)
    maximum_wait_minutes: float = Field(ge=0)
    throughput: int = Field(ge=0)
    utilization_ratio: float = Field(ge=0)
    remaining_voters: int = Field(ge=0)
    bottleneck: bool


class SimulationEngineResult(BaseModel):
    status: Literal["succeeded", "not_implemented", "failed"]
    units: list[PollingUnitSimulationResult] = Field(default_factory=list)
    explanation: str
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SimulationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scenario_id: uuid.UUID
    equipment_plan_id: uuid.UUID | None
    assumption_version_id: uuid.UUID
    status: str
    progress_stage: str
    engine_name: str
    engine_version: str
    contract_version: str
    input_snapshot: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None
