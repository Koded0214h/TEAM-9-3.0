"""Add versioned voter-capacity rules."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261119_0005"
down_revision = "20261119_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacity_rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True)),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("target_voters", sa.Integer(), nullable=False),
        sa.Column("maximum_voters", sa.Integer(), nullable=False),
        sa.Column("underutilized_ratio", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ward_id", "version", name="uq_capacity_rule_ward_version"),
    )
    op.create_index("ix_capacity_rule_versions_ward_id", "capacity_rule_versions", ["ward_id"])


def downgrade() -> None:
    op.drop_table("capacity_rule_versions")
