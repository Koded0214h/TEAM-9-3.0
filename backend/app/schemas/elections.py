import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ElectionType = Literal[
    "presidential", "governorship", "senatorial", "representative", "state_assembly"
]
FormType = Literal["EC8A", "EC8B", "EC8C", "EC8D"]
GeographyLevel = Literal["polling_unit", "ward", "lga", "state"]


class ElectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    election_type: ElectionType
    election_date: date
    jurisdiction: str = Field(min_length=1, max_length=160)


class ElectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    election_type: str
    election_date: date
    jurisdiction: str
    status: str


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    code: str = Field(min_length=1, max_length=30)
    is_monitored: bool = False


class PartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str
    is_monitored: bool


class ContestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    office: ElectionType
    form_type: FormType
    geography_level: GeographyLevel


class ContestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    election_id: uuid.UUID
    name: str
    office: str
    form_type: str
    geography_level: str
    status: str


class CandidateCreate(BaseModel):
    party_id: uuid.UUID
    name: str = Field(min_length=1, max_length=180)
    ballot_code: str = Field(min_length=1, max_length=30)


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contest_id: uuid.UUID
    party_id: uuid.UUID
    name: str
    ballot_code: str


class CoverageCreate(BaseModel):
    geography_node_ids: list[uuid.UUID] = Field(min_length=1)
