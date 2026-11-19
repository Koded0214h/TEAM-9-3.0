import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_type", "version", name="uq_dataset_type_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_type: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(255))
    classification: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    checksum: Mapped[str | None] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportJob(Base):
    __tablename__ = "import_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    filename: Mapped[str] = mapped_column(String(255))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class State(Base):
    __tablename__ = "states"
    __table_args__ = (UniqueConstraint("dataset_id", "code", name="uq_state_dataset_code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120), index=True)
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    lgas: Mapped[list["LGA"]] = relationship(back_populates="state")


class LGA(Base):
    __tablename__ = "lgas"
    __table_args__ = (UniqueConstraint("dataset_id", "code", name="uq_lga_dataset_code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("states.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120), index=True)
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    state: Mapped[State] = relationship(back_populates="lgas")
    wards: Mapped[list["Ward"]] = relationship(back_populates="lga")


class Ward(Base):
    __tablename__ = "wards"
    __table_args__ = (UniqueConstraint("dataset_id", "code", name="uq_ward_dataset_code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    lga_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lgas.id"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120), index=True)
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    lga: Mapped[LGA] = relationship(back_populates="wards")
    registration_areas: Mapped[list["RegistrationArea"]] = relationship(back_populates="ward")


class RegistrationArea(Base):
    __tablename__ = "registration_areas"
    __table_args__ = (UniqueConstraint("dataset_id", "code", name="uq_ra_dataset_code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120), index=True)
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    ward: Mapped[Ward] = relationship(back_populates="registration_areas")


class PollingUnit(Base):
    __tablename__ = "polling_units"
    __table_args__ = (UniqueConstraint("dataset_id", "code", name="uq_polling_unit_dataset_code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    registration_area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registration_areas.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(180), index=True)
    address: Mapped[str] = mapped_column(String(500))
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=True), nullable=False)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    registered_voters: Mapped[int] = mapped_column(Integer, default=0)


class GeospatialLayer(Base):
    __tablename__ = "geospatial_layers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    layer_type: Mapped[str] = mapped_column(String(40))
    attribution: Mapped[str | None] = mapped_column(String(500))
    style: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class GeospatialFeature(Base):
    __tablename__ = "geospatial_features"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geospatial_layers.id", ondelete="CASCADE"), index=True
    )
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    geometry = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=True), nullable=False)
