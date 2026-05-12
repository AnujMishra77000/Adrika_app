"""enquiry status timeline

Revision ID: 202604200002
Revises: 202604200001
Create Date: 2026-04-20 14:45:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604200002"
down_revision = "202604200001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "student_enquiry_status_history"):
        op.create_table(
            "student_enquiry_status_history",
            sa.Column("enquiry_id", sa.Uuid(as_uuid=False), sa.ForeignKey("student_enquiries.id", ondelete="CASCADE"), nullable=False),
            sa.Column("from_status", sa.String(length=20), nullable=True),
            sa.Column("to_status", sa.String(length=20), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("changed_by_user_id", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "from_status IS NULL OR from_status IN ('interested', 'follow_up', 'confirmed', 'not_interested')",
                name="ck_enquiry_history_from_status",
            ),
            sa.CheckConstraint(
                "to_status IN ('interested', 'follow_up', 'confirmed', 'not_interested')",
                name="ck_enquiry_history_to_status",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "student_enquiry_status_history") and not _index_exists(
        inspector, "student_enquiry_status_history", "ix_enquiry_history_enquiry_changed"
    ):
        op.create_index(
            "ix_enquiry_history_enquiry_changed",
            "student_enquiry_status_history",
            ["enquiry_id", "changed_at"],
        )


def downgrade() -> None:
    # Intentionally non-destructive for production safety.
    pass
