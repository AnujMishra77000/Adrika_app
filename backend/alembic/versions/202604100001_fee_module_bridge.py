"""fee module compatibility bridge

Revision ID: 202604100001
Revises: 202604080001
Create Date: 2026-04-10 15:55:00

This revision intentionally contains no schema changes.
It exists to bridge older local databases that were stamped
with 202604100001 so that subsequent migrations can run.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "202604100001"
down_revision = "202604080001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op bridge migration.
    pass


def downgrade() -> None:
    # No-op bridge migration.
    pass
