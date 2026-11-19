import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SimulationAssumptionVersion(Base):
    __tablename__ = "simulation_assumption_versions"
    __table_args__ = (
        UniqueConstraint("ward_id", "version", name="uq_simulation_assumption_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    voting_period_minutes: Mapped[int] = mapped_column(Integer)
    arrival_pattern: Mapped[dict[str, Any]] = mapped_column(JSON)
    average_service_minutes: Mapped[float] = mapped_column(Float)
    default_staff_count: Mapped[int] = mapped_column(Integer)
    equipment_uptime_ratio: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    explanation: Mapped[str] = mapped_column(String(500))
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), index=True
    )
    equipment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_plans.id")
    )
    assumption_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_assumption_versions.id")
    )
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    progress_stage: Mapped[str] = mapped_column(String(120), default="queued")
    engine_name: Mapped[str] = mapped_column(String(100))
    engine_version: Mapped[str] = mapped_column(String(80))
    contract_version: Mapped[str] = mapped_column(String(20), default="1.0")
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
