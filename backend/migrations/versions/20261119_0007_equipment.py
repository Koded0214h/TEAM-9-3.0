"""Add equipment catalogue, inventory, rules, plans, and overrides."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261119_0007"
down_revision = "20261119_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_types_code", "equipment_types", ["code"], unique=True)
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_snapshots_ward_id", "inventory_snapshots", ["ward_id"])
    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("available_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["inventory_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "equipment_type_id", name="uq_inventory_equipment"),
    )
    op.create_index("ix_inventory_items_snapshot_id", "inventory_items", ["snapshot_id"])
    op.create_index(
        "ix_inventory_items_equipment_type_id", "inventory_items", ["equipment_type_id"]
    )
    op.create_table(
        "equipment_rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True)),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("fixed_minimum", sa.Integer(), nullable=False),
        sa.Column("voters_per_item", sa.Integer()),
        sa.Column("maximum_quantity", sa.Integer()),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "equipment_type_id", "ward_id", "version", name="uq_equipment_rule_version"
        ),
    )
    op.create_index(
        "ix_equipment_rule_versions_equipment_type_id",
        "equipment_rule_versions",
        ["equipment_type_id"],
    )
    op.create_index("ix_equipment_rule_versions_ward_id", "equipment_rule_versions", ["ward_id"])
    op.create_table(
        "equipment_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_snapshot_id"], ["inventory_snapshots.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_plans_scenario_id", "equipment_plans", ["scenario_id"])
    op.create_index("ix_equipment_plans_status", "equipment_plans", ["status"])
    op.create_table(
        "equipment_plan_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("polling_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voter_count", sa.Integer(), nullable=False),
        sa.Column("demanded_quantity", sa.Integer(), nullable=False),
        sa.Column("allocated_quantity", sa.Integer(), nullable=False),
        sa.Column("shortage_quantity", sa.Integer(), nullable=False),
        sa.Column("surplus_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["equipment_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["equipment_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id", "polling_unit_id", "equipment_type_id", name="uq_plan_unit_equipment"
        ),
    )
    for column in ("plan_id", "polling_unit_id", "equipment_type_id"):
        op.create_index(f"ix_equipment_plan_items_{column}", "equipment_plan_items", [column])
    op.create_table(
        "equipment_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculated_quantity", sa.Integer(), nullable=False),
        sa.Column("overridden_quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["plan_item_id"], ["equipment_plan_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_overrides_plan_item_id", "equipment_overrides", ["plan_item_id"])


def downgrade() -> None:
    for table in (
        "equipment_overrides",
        "equipment_plan_items",
        "equipment_plans",
        "equipment_rule_versions",
        "inventory_items",
        "inventory_snapshots",
        "equipment_types",
    ):
        op.drop_table(table)
