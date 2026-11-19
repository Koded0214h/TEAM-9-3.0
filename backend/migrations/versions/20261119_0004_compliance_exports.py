"""compliance, irev, and exports

Revision ID: 20261119_0004
"""

from alembic import op

from app.db.base import Base

revision = "20261119_0004"
down_revision = "20261119_0003"
branch_labels = None
depends_on = None

TABLES = [
    "audit_events",
    "evidence_integrity_checks",
    "legal_holds",
    "irev_records",
    "export_jobs",
]


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in TABLES]
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in reversed(TABLES)]
    )
