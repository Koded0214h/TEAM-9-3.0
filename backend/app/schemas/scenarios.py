import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    planning_ward_id: uuid.UUID


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    status: Literal["draft", "ready_for_review", "reviewed", "archived"] | None = None
    expected_revision: int = Field(ge=1)


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    planning_ward_id: uuid.UUID
    baseline_polling_dataset_id: uuid.UUID
    baseline_geography_dataset_id: uuid.UUID
    status: str
    revision: int
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PollingUnitChangeCreate(BaseModel):
    change_type: Literal["proposed_new", "relocated", "deactivated"]
    baseline_polling_unit_id: uuid.UUID | None = None
    code: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    registered_voters: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=3)
    expected_revision: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_change(self):
        if self.change_type == "proposed_new":
            if not all(
                [
                    self.code,
                    self.name,
                    self.address,
                    self.latitude is not None,
                    self.longitude is not None,
                ]
            ):
                raise ValueError(
                    "New proposals require code, name, address, latitude, and longitude"
                )
        elif self.baseline_polling_unit_id is None:
            raise ValueError("Relocation and deactivation require a baseline polling unit")
        if self.change_type == "relocated" and (self.latitude is None or self.longitude is None):
            raise ValueError("Relocation requires latitude and longitude")
        return self


class PollingUnitChangeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    registered_voters: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, min_length=3)
    expected_revision: int = Field(ge=1)


class PollingUnitChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scenario_id: uuid.UUID
    baseline_polling_unit_id: uuid.UUID | None
    change_type: str
    code: str | None
    name: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    registered_voters: int | None
    reason: str
    created_at: datetime
    updated_at: datetime


class EffectivePollingUnit(BaseModel):
    id: uuid.UUID
    baseline_polling_unit_id: uuid.UUID | None
    change_id: uuid.UUID | None
    source: Literal["official", "proposed", "modified"]
    code: str
    name: str
    address: str
    latitude: float
    longitude: float
    status: str
    registered_voters: int
