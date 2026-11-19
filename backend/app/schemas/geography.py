import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    dataset_type: Literal[
        "administrative_geography",
        "polling_units",
        "geospatial_context",
        "equipment",
        "assumptions",
    ]
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=255)
    classification: Literal["official", "sample", "synthetic"]
    notes: str | None = None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dataset_type: str
    name: str
    version: str
    source: str
    classification: str
    status: str
    checksum: str | None
    row_count: int
    is_active: bool
    notes: str | None
    created_at: datetime


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[dict[str, Any]]


class GeographyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str


class ResolvePointRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ResolvePointResponse(BaseModel):
    state: GeographyResponse | None = None
    lga: GeographyResponse | None = None
    ward: GeographyResponse | None = None
    registration_area: GeographyResponse | None = None


class PollingUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    address: str
    latitude: float
    longitude: float
    ward_id: uuid.UUID
    registration_area_id: uuid.UUID | None
    status: str
    registered_voters: int


class PollingUnitListResponse(BaseModel):
    items: list[PollingUnitResponse]
    total: int
    dataset_classification: str


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]
