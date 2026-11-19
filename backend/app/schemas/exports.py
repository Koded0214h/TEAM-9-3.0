import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExportCreate(BaseModel):
    format: Literal["json", "csv"]


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scenario_id: uuid.UUID
    format: str
    status: str
    filename: str
    content_type: str
    error: str | None
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime
