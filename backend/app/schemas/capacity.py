import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapacityRuleCreate(BaseModel):
    ward_id: uuid.UUID | None = None
    version: str = Field(min_length=1, max_length=80)
    target_voters: int = Field(gt=0)
    maximum_voters: int = Field(gt=0)
    underutilized_ratio: float = Field(gt=0, lt=1)
    explanation: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def maximum_must_cover_target(self):
        if self.maximum_voters < self.target_voters:
            raise ValueError("maximum_voters must be greater than or equal to target_voters")
        return self


class CapacityRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ward_id: uuid.UUID | None
    version: str
    target_voters: int
    maximum_voters: int
    underutilized_ratio: float
    is_active: bool
    explanation: str


class PollingUnitLoad(BaseModel):
    polling_unit_id: uuid.UUID
    code: str
    name: str
    registered_voters: int
    target_voters: int
    maximum_voters: int
    load_ratio: float
    classification: Literal["underutilized", "within_capacity", "overloaded"]
    source: str


class LoadAnalysisResponse(BaseModel):
    scenario_id: uuid.UUID
    rule: CapacityRuleResponse
    units: list[PollingUnitLoad]
    overloaded_count: int
    underutilized_count: int
    within_capacity_count: int
