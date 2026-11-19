"""Add scenario management and polling-unit overlays."""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = "20261119_0004"
down_revision = "20261119_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("planning_ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_polling_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_geography_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["planning_ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["baseline_polling_dataset_id"], ["dataset_versions.id"]),
        sa.ForeignKeyConstraint(["baseline_geography_dataset_id"], ["dataset_versions.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("name", "planning_ward_id", "status", "created_by_id"):
        op.create_index(f"ix_scenarios_{column}", "scenarios", [column])
    op.create_table(
        "scenario_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_revisions_scenario_id", "scenario_revisions", ["scenario_id"])
    op.create_table(
        "scenario_polling_unit_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_polling_unit_id", postgresql.UUID(as_uuid=True)),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("code", sa.String(60)),
        sa.Column("name", sa.String(180)),
        sa.Column("address", sa.String(500)),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=True)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("registered_voters", sa.Integer()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["baseline_polling_unit_id"], ["polling_units.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scenario_id", "baseline_polling_unit_id", name="uq_scenario_baseline_unit_change"
        ),
    )
    for column in ("scenario_id", "baseline_polling_unit_id", "change_type"):
        op.create_index(
            f"ix_scenario_polling_unit_changes_{column}",
            "scenario_polling_unit_changes",
            [column],
        )


def downgrade() -> None:
    op.drop_table("scenario_polling_unit_changes")
    op.drop_table("scenario_revisions")
    op.drop_table("scenarios")
