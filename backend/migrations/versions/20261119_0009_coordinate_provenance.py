"""Add polling-unit coordinate provenance."""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0009"
down_revision = "20261119_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "polling_units",
        sa.Column("coordinate_source", sa.String(40), server_default="imported", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("polling_units", "coordinate_source")
