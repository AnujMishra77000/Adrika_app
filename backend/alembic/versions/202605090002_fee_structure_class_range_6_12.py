"""expand fee structure class range to 6-12

Revision ID: 202605090002
Revises: 202605090001
Create Date: 2026-05-09 20:05:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "202605090002"
down_revision = "202605090001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _check_exists(inspector: sa.Inspector, table_name: str, check_name: str) -> bool:
    return any((check.get("name") or "") == check_name for check in inspector.get_check_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "fee_structures"):
        return

    # SQLite-safe check update via batch recreate.
    with op.batch_alter_table("fee_structures", recreate="always") as batch_op:
        if _check_exists(inspector, "fee_structures", "ck_fee_structure_class_level"):
            batch_op.drop_constraint("ck_fee_structure_class_level", type_="check")
        batch_op.create_check_constraint(
            "ck_fee_structure_class_level",
            "class_level IN (6, 7, 8, 9, 10, 11, 12)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "fee_structures"):
        return

    with op.batch_alter_table("fee_structures", recreate="always") as batch_op:
        if _check_exists(inspector, "fee_structures", "ck_fee_structure_class_level"):
            batch_op.drop_constraint("ck_fee_structure_class_level", type_="check")
        batch_op.create_check_constraint(
            "ck_fee_structure_class_level",
            "class_level IN (10, 11, 12)",
        )
