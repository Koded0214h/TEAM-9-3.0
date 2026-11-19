import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EquipmentTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=160)
    unit: str = Field(default="items", min_length=1, max_length=40)
    description: str | None = None


class EquipmentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    unit: str
    description: str | None
    is_active: bool


class InventoryItemInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    equipment_type_id: uuid.UUID
    available_quantity: int = Field(ge=0)


class InventoryCreate(BaseModel):
    ward_id: uuid.UUID
    version: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=255)
    classification: str = Field(pattern="^(official|sample|synthetic)$")
    items: list[InventoryItemInput] = Field(min_length=1)


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ward_id: uuid.UUID
    version: str
    source: str
    classification: str
    is_active: bool
    items: list[InventoryItemInput]


class EquipmentRuleCreate(BaseModel):
    equipment_type_id: uuid.UUID
    ward_id: uuid.UUID | None = None
    version: str = Field(min_length=1, max_length=80)
    fixed_minimum: int = Field(ge=0)
    voters_per_item: int | None = Field(default=None, gt=0)
    maximum_quantity: int | None = Field(default=None, ge=0)
    priority: int = Field(default=100, ge=1)
    explanation: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def validate_rule(self):
        if self.fixed_minimum == 0 and self.voters_per_item is None:
            raise ValueError("A fixed minimum or voters_per_item rule is required")
        if self.maximum_quantity is not None and self.maximum_quantity < self.fixed_minimum:
            raise ValueError("maximum_quantity cannot be below fixed_minimum")
        return self


class EquipmentRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    equipment_type_id: uuid.UUID
    ward_id: uuid.UUID | None
    version: str
    fixed_minimum: int
    voters_per_item: int | None
    maximum_quantity: int | None
    priority: int
    is_active: bool
    explanation: str


class EquipmentOverrideCreate(BaseModel):
    quantity: int = Field(ge=0)
    reason: str = Field(min_length=3)


class EquipmentOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    calculated_quantity: int
    overridden_quantity: int
    reason: str
    created_by_id: uuid.UUID
    created_at: datetime


class EquipmentPlanItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    polling_unit_id: uuid.UUID
    equipment_type_id: uuid.UUID
    rule_id: uuid.UUID
    voter_count: int
    demanded_quantity: int
    allocated_quantity: int
    shortage_quantity: int
    surplus_quantity: int
    overrides: list[EquipmentOverrideResponse]


class EquipmentPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scenario_id: uuid.UUID
    inventory_snapshot_id: uuid.UUID
    status: str
    input_snapshot: dict
    created_at: datetime
    items: list[EquipmentPlanItemResponse]
