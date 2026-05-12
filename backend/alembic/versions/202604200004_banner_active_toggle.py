"""add banner active toggle

Revision ID: 202604200004
Revises: 202604200003
Create Date: 2026-04-20 21:05:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604200004"
down_revision = "202604200003"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "banners") and not _column_exists(inspector, "banners", "is_active"):
        op.add_column(
            "banners",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "banners") and not _index_exists(
        inspector,
        "banners",
        "ix_banners_is_active_window",
    ):
        op.create_index(
            "ix_banners_is_active_window",
            "banners",
            ["is_active", "active_from", "active_to"],
        )


def downgrade() -> None:
    # Intentionally non-destructive for production safety.
    pass
