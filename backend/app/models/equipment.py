import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EquipmentType(Base):
    __tablename__ = "equipment_types"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str] = mapped_column(String(40), default="items")
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(255))
    classification: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["InventoryItem"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "equipment_type_id", name="uq_inventory_equipment"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_snapshots.id", ondelete="CASCADE"), index=True
    )
    equipment_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_types.id"), index=True
    )
    available_quantity: Mapped[int] = mapped_column(Integer)


class EquipmentRuleVersion(Base):
    __tablename__ = "equipment_rule_versions"
    __table_args__ = (
        UniqueConstraint(
            "equipment_type_id", "ward_id", "version", name="uq_equipment_rule_version"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_types.id"), index=True
    )
    ward_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    fixed_minimum: Mapped[int] = mapped_column(Integer, default=0)
    voters_per_item: Mapped[int | None] = mapped_column(Integer)
    maximum_quantity: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    explanation: Mapped[str] = mapped_column(String(500))
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentPlan(Base):
    __tablename__ = "equipment_plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), index=True
    )
    inventory_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_snapshots.id")
    )
    status: Mapped[str] = mapped_column(String(30), default="succeeded", index=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["EquipmentPlanItem"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class EquipmentPlanItem(Base):
    __tablename__ = "equipment_plan_items"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "polling_unit_id", "equipment_type_id", name="uq_plan_unit_equipment"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_plans.id", ondelete="CASCADE"), index=True
    )
    polling_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    equipment_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_types.id"), index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_rule_versions.id")
    )
    voter_count: Mapped[int] = mapped_column(Integer)
    demanded_quantity: Mapped[int] = mapped_column(Integer)
    allocated_quantity: Mapped[int] = mapped_column(Integer)
    shortage_quantity: Mapped[int] = mapped_column(Integer)
    surplus_quantity: Mapped[int] = mapped_column(Integer)
    overrides: Mapped[list["EquipmentOverride"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class EquipmentOverride(Base):
    __tablename__ = "equipment_overrides"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_plan_items.id", ondelete="CASCADE"), index=True
    )
    calculated_quantity: Mapped[int] = mapped_column(Integer)
    overridden_quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
