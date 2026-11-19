"""identity and workspaces

Revision ID: 20261119_0001
"""

from alembic import op

from app.db.base import Base

revision = "20261119_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
