import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CapacityRuleVersion(Base):
    __tablename__ = "capacity_rule_versions"
    __table_args__ = (UniqueConstraint("ward_id", "version", name="uq_capacity_rule_ward_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    target_voters: Mapped[int] = mapped_column(Integer)
    maximum_voters: Mapped[int] = mapped_column(Integer)
    underutilized_ratio: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    explanation: Mapped[str] = mapped_column(String(500))
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
