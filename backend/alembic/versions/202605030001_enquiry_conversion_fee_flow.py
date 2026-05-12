"""enquiry conversion and fee flow fields

Revision ID: 202605030001
Revises: 202604220001
Create Date: 2026-05-03 19:15:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202605030001"
down_revision = "202604220001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "student_enquiries"):
        return

    columns_to_add = [
        ("batch_id", sa.String(length=36), True),
        ("manual_fee_amount", sa.Numeric(10, 2), True),
        ("manual_fee_installment_count", sa.Integer(), True),
        ("initial_fee_paid_amount", sa.Numeric(10, 2), True),
        ("initial_fee_paid_on", sa.DateTime(timezone=True), True),
        ("initial_fee_payment_mode", sa.String(length=30), True),
        ("initial_fee_reference_no", sa.String(length=120), True),
        ("initial_fee_note", sa.String(length=500), True),
        ("converted_student_id", sa.String(length=36), True),
        ("converted_at", sa.DateTime(timezone=True), True),
    ]

    for column_name, column_type, nullable in columns_to_add:
        if not _column_exists(inspector, "student_enquiries", column_name):
            op.add_column(
                "student_enquiries",
                sa.Column(column_name, column_type, nullable=nullable),
            )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "student_enquiries", "ix_student_enquiry_batch"):
        op.create_index(
            "ix_student_enquiry_batch",
            "student_enquiries",
            ["batch_id"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "student_enquiries", "ix_student_enquiry_converted_student"):
        op.create_index(
            "ix_student_enquiry_converted_student",
            "student_enquiries",
            ["converted_student_id"],
            unique=False,
        )


def downgrade() -> None:
    # Non-destructive downgrade by design.
    pass
