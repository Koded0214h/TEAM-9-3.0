"""Add voter-allocation engine run contracts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261119_0006"
down_revision = "20261119_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allocation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("progress_stage", sa.String(120), nullable=False),
        sa.Column("engine_name", sa.String(100), nullable=False),
        sa.Column("engine_version", sa.String(80), nullable=False),
        sa.Column("contract_version", sa.String(20), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("is_selected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allocation_runs_scenario_id", "allocation_runs", ["scenario_id"])
    op.create_index("ix_allocation_runs_status", "allocation_runs", ["status"])


def downgrade() -> None:
    op.drop_table("allocation_runs")
