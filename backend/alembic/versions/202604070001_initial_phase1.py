"""initial phase1 schema

Revision ID: 202604070001
Revises:
Create Date: 2026-04-07 01:20:00
"""

from alembic import op

from app.db.base import Base
from app.db.models import *  # noqa: F401,F403

# revision identifiers, used by Alembic.
revision = "202604070001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
