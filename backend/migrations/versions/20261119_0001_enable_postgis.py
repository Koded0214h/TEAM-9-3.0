"""Enable PostGIS.

Revision ID: 20261119_0001
Revises:
Create Date: 2026-11-19
"""

from alembic import op

revision: str = "20261119_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis")
