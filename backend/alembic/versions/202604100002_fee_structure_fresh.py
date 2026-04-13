"""fresh fee structure section foundation

Revision ID: 202604100002
Revises: 202604100001
Create Date: 2026-04-10 16:05:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604100002"
down_revision = "202604100001"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("fee_structures"):
        op.create_table(
            "fee_structures",
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("stream", sa.String(length=20), nullable=True),
            sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("installment_count", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("class_level IN (10, 11, 12)", name="ck_fee_structure_class_level"),
            sa.CheckConstraint("stream IS NULL OR stream IN ('science', 'commerce')", name="ck_fee_structure_stream"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("fee_structures") and not _has_index(
        inspector, "fee_structures", "ix_fee_structure_class_stream_active"
    ):
        op.create_index(
            "ix_fee_structure_class_stream_active",
            "fee_structures",
            ["class_level", "stream", "is_active"],
            unique=False,
        )

    # Compatibility columns for fee invoice / payment transaction models.
    inspector = sa.inspect(bind)
    if inspector.has_table("fee_invoices"):
        if not _has_column(inspector, "fee_invoices", "student_fee_account_id"):
            op.add_column("fee_invoices", sa.Column("student_fee_account_id", sa.String(length=36), nullable=True))
        if not _has_column(inspector, "fee_invoices", "installment_id"):
            op.add_column("fee_invoices", sa.Column("installment_id", sa.String(length=36), nullable=True))
        if not _has_column(inspector, "fee_invoices", "installment_no"):
            op.add_column("fee_invoices", sa.Column("installment_no", sa.Integer(), nullable=True))
        if not _has_column(inspector, "fee_invoices", "balance_amount"):
            op.add_column("fee_invoices", sa.Column("balance_amount", sa.Numeric(precision=10, scale=2), nullable=True))
        if not _has_column(inspector, "fee_invoices", "payment_link"):
            op.add_column("fee_invoices", sa.Column("payment_link", sa.String(length=1024), nullable=True))
        if not _has_column(inspector, "fee_invoices", "next_installment_date"):
            op.add_column("fee_invoices", sa.Column("next_installment_date", sa.Date(), nullable=True))
        if not _has_column(inspector, "fee_invoices", "reminder_enabled"):
            op.add_column(
                "fee_invoices",
                sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            )
            op.alter_column("fee_invoices", "reminder_enabled", server_default=None)
        if not _has_column(inspector, "fee_invoices", "last_reminder_sent_at"):
            op.add_column("fee_invoices", sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True))

        inspector = sa.inspect(bind)
        if not _has_index(inspector, "fee_invoices", "ix_fee_invoice_reminder_due"):
            op.create_index(
                "ix_fee_invoice_reminder_due",
                "fee_invoices",
                ["reminder_enabled", "next_installment_date", "due_date"],
                unique=False,
            )
        if not _has_index(inspector, "fee_invoices", "ix_fee_invoice_account_status"):
            op.create_index(
                "ix_fee_invoice_account_status",
                "fee_invoices",
                ["student_fee_account_id", "status"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("payment_transactions"):
        if not _has_column(inspector, "payment_transactions", "student_fee_account_id"):
            op.add_column(
                "payment_transactions", sa.Column("student_fee_account_id", sa.String(length=36), nullable=True)
            )
        if not _has_column(inspector, "payment_transactions", "payment_mode"):
            op.add_column(
                "payment_transactions",
                sa.Column("payment_mode", sa.String(length=30), nullable=False, server_default="manual"),
            )
            op.alter_column("payment_transactions", "payment_mode", server_default=None)
        if not _has_column(inspector, "payment_transactions", "note"):
            op.add_column("payment_transactions", sa.Column("note", sa.Text(), nullable=True))
        if not _has_column(inspector, "payment_transactions", "receipt_generated"):
            op.add_column(
                "payment_transactions",
                sa.Column("receipt_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
            op.alter_column("payment_transactions", "receipt_generated", server_default=None)

        inspector = sa.inspect(bind)
        if not _has_index(inspector, "payment_transactions", "ix_payment_account_status"):
            op.create_index(
                "ix_payment_account_status",
                "payment_transactions",
                ["student_fee_account_id", "status"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("fee_structures"):
        if _has_index(inspector, "fee_structures", "ix_fee_structure_class_stream_active"):
            op.drop_index("ix_fee_structure_class_stream_active", table_name="fee_structures")
        op.drop_table("fee_structures")
