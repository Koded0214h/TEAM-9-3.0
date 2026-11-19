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
    names = {
        "users",
        "workspaces",
        "memberships",
        "geography_nodes",
        "geography_assignments",
        "refresh_sessions",
        "mfa_recovery_codes",
        "invitations",
    }
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in names]
    )


def downgrade() -> None:
    names = [
        "invitations",
        "mfa_recovery_codes",
        "refresh_sessions",
        "geography_assignments",
        "geography_nodes",
        "memberships",
        "workspaces",
        "users",
    ]
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in names]
    )
