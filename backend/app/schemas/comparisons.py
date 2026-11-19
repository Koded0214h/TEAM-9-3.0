import uuid
from typing import Any

from pydantic import BaseModel


class ChangeSummary(BaseModel):
    added: int
    relocated: int
    deactivated: int
    unchanged: int


class MetricValue(BaseModel):
    status: str
    baseline: float | int | None = None
    scenario: float | int | None = None
    delta: float | int | None = None
    unit: str | None = None
    explanation: str


class ScenarioComparisonResponse(BaseModel):
    scenario_id: uuid.UUID
    scenario_revision: int
    baseline_polling_dataset_id: uuid.UUID
    baseline_geography_dataset_id: uuid.UUID
    compatible: bool
    changes: ChangeSummary
    polling_units: list[dict[str, Any]]
    metrics: dict[str, MetricValue]
    explanations: list[str]
    warnings: list[str]
