"""syllabus completion hours

Revision ID: 202604200003
Revises: 202604200002
Create Date: 2026-04-20 18:45:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604200003"
down_revision = "202604200002"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "subject_academic_scopes") and not _column_exists(
        inspector, "subject_academic_scopes", "estimated_hours"
    ):
        op.add_column(
            "subject_academic_scopes",
            sa.Column("estimated_hours", sa.Integer(), nullable=False, server_default="0"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "lecture_schedules") and not _column_exists(
        inspector, "lecture_schedules", "duration_minutes"
    ):
        op.add_column(
            "lecture_schedules",
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        )


def downgrade() -> None:
    # Intentionally non-destructive for production safety.
    pass

