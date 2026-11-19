"""election configuration and result intake

Revision ID: 20261119_0002
"""

from alembic import op

from app.db.base import Base

revision = "20261119_0002"
down_revision = "20261119_0001"
branch_labels = None
depends_on = None


TABLES = [
    "elections",
    "political_parties",
    "contests",
    "candidates",
    "election_coverage",
    "documents",
    "result_submissions",
    "result_figures",
]


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in TABLES]
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in reversed(TABLES)]
    )
