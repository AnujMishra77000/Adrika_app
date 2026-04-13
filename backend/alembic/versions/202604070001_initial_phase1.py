"""initial phase1 schema

Revision ID: 202604070001
Revises:
Create Date: 2026-04-07 01:20:00
"""

from pathlib import Path
import sys

from alembic import op

# Keep migration importable even when Alembic is invoked without PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
