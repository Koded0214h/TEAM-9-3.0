"""Add simulation assumptions and engine run contracts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261119_0008"
down_revision = "20261119_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_assumption_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True)),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("voting_period_minutes", sa.Integer(), nullable=False),
        sa.Column("arrival_pattern", sa.JSON(), nullable=False),
        sa.Column("average_service_minutes", sa.Float(), nullable=False),
        sa.Column("default_staff_count", sa.Integer(), nullable=False),
        sa.Column("equipment_uptime_ratio", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ward_id", "version", name="uq_simulation_assumption_version"),
    )
    op.create_index(
        "ix_simulation_assumption_versions_ward_id", "simulation_assumption_versions", ["ward_id"]
    )
    op.create_table(
        "simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_plan_id", postgresql.UUID(as_uuid=True)),
        sa.Column("assumption_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("progress_stage", sa.String(120), nullable=False),
        sa.Column("engine_name", sa.String(100), nullable=False),
        sa.Column("engine_version", sa.String(80), nullable=False),
        sa.Column("contract_version", sa.String(20), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_plan_id"], ["equipment_plans.id"]),
        sa.ForeignKeyConstraint(["assumption_version_id"], ["simulation_assumption_versions.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_runs_scenario_id", "simulation_runs", ["scenario_id"])
    op.create_index("ix_simulation_runs_status", "simulation_runs", ["status"])


def downgrade() -> None:
    op.drop_table("simulation_runs")
    op.drop_table("simulation_assumption_versions")
