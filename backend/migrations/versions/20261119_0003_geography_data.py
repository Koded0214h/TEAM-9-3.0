"""Add versioned geography and polling-unit data."""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = "20261119_0003"
down_revision = "20261119_0002"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False)


def upgrade() -> None:
    op.create_table(
        "dataset_versions",
        _id(),
        sa.Column("dataset_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("checksum", sa.String(64)),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_type", "version", name="uq_dataset_type_version"),
    )
    op.create_index("ix_dataset_versions_dataset_type", "dataset_versions", ["dataset_type"])
    op.create_index("ix_dataset_versions_status", "dataset_versions", ["status"])
    op.create_table(
        "import_jobs",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_dataset_id", "import_jobs", ["dataset_id"])
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])
    op.create_table(
        "states",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326)),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "code", name="uq_state_dataset_code"),
    )
    op.create_index("ix_states_dataset_id", "states", ["dataset_id"])
    op.create_index("ix_states_name", "states", ["name"])
    op.create_table(
        "lgas",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326)),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "code", name="uq_lga_dataset_code"),
    )
    op.create_index("ix_lgas_dataset_id", "lgas", ["dataset_id"])
    op.create_index("ix_lgas_state_id", "lgas", ["state_id"])
    op.create_index("ix_lgas_name", "lgas", ["name"])
    op.create_table(
        "wards",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lga_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326)),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lga_id"], ["lgas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "code", name="uq_ward_dataset_code"),
    )
    op.create_index("ix_wards_dataset_id", "wards", ["dataset_id"])
    op.create_index("ix_wards_lga_id", "wards", ["lga_id"])
    op.create_index("ix_wards_name", "wards", ["name"])
    op.create_table(
        "registration_areas",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326)),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "code", name="uq_ra_dataset_code"),
    )
    op.create_index("ix_registration_areas_dataset_id", "registration_areas", ["dataset_id"])
    op.create_index("ix_registration_areas_ward_id", "registration_areas", ["ward_id"])
    op.create_index("ix_registration_areas_name", "registration_areas", ["name"])
    op.create_table(
        "polling_units",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registration_area_id", postgresql.UUID(as_uuid=True)),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("registered_voters", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["registration_area_id"], ["registration_areas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "code", name="uq_polling_unit_dataset_code"),
    )
    for name, column in (
        ("dataset_id", "dataset_id"),
        ("ward_id", "ward_id"),
        ("registration_area_id", "registration_area_id"),
        ("name", "name"),
        ("status", "status"),
    ):
        op.create_index(f"ix_polling_units_{name}", "polling_units", [column])
    op.create_table(
        "geospatial_layers",
        _id(),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("layer_type", sa.String(40), nullable=False),
        sa.Column("attribution", sa.String(500)),
        sa.Column("style", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geospatial_layers_dataset_id", "geospatial_layers", ["dataset_id"])
    op.create_table(
        "geospatial_features",
        _id(),
        sa.Column("layer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326, spatial_index=True), nullable=False),
        sa.ForeignKeyConstraint(["layer_id"], ["geospatial_layers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geospatial_features_layer_id", "geospatial_features", ["layer_id"])


def downgrade() -> None:
    for table in (
        "geospatial_features",
        "geospatial_layers",
        "polling_units",
        "registration_areas",
        "wards",
        "lgas",
        "states",
        "import_jobs",
        "dataset_versions",
    ):
        op.drop_table(table)
