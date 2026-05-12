"""student credential snapshot for admin visibility

Revision ID: 202605090001
Revises: 202605050001
Create Date: 2026-05-09 19:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202605090001"
down_revision = "202605050001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "student_credentials"):
        op.create_table(
            "student_credentials",
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("login_id", sa.String(length=20), nullable=False),
            sa.Column("password_plain", sa.String(length=128), nullable=False),
            sa.Column("password_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_student_credentials_user_id"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "student_credentials") and not _index_exists(inspector, "student_credentials", "ix_student_credentials_login_id"):
        op.create_index("ix_student_credentials_login_id", "student_credentials", ["login_id"], unique=False)


def downgrade() -> None:
    # Non-destructive downgrade by design.
    pass
