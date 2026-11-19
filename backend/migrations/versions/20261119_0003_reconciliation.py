"""reconciliation and investigations

Revision ID: 20261119_0003
"""

from alembic import op

from app.db.base import Base

revision = "20261119_0003"
down_revision = "20261119_0002"
branch_labels = None
depends_on = None

TABLES = [
    "reconciliation_runs",
    "discrepancies",
    "discrepancy_comments",
    "discrepancy_status_history",
]


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in TABLES]
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in reversed(TABLES)]
    )
