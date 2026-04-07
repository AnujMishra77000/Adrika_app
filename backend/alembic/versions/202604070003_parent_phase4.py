"""add parent and billing phase4 tables

Revision ID: 202604070003
Revises: 202604070002
Create Date: 2026-04-07 11:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604070003"
down_revision = "202604070002"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("parent_profiles"):
        op.create_table(
            "parent_profiles",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("parent_student_links"):
        op.create_table(
            "parent_student_links",
            sa.Column("parent_id", sa.String(length=36), nullable=False),
            sa.Column("student_id", sa.String(length=36), nullable=False),
            sa.Column("relation_type", sa.String(length=30), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["parent_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id", "student_id", name="uq_parent_student_link"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("parent_student_links"):
        if not _has_index(inspector, "parent_student_links", "ix_parent_link_parent_active"):
            op.create_index("ix_parent_link_parent_active", "parent_student_links", ["parent_id", "is_active"], unique=False)
        if not _has_index(inspector, "parent_student_links", "ix_parent_link_student_active"):
            op.create_index("ix_parent_link_student_active", "parent_student_links", ["student_id", "is_active"], unique=False)

    inspector = sa.inspect(bind)
    if not inspector.has_table("parent_communication_preferences"):
        op.create_table(
            "parent_communication_preferences",
            sa.Column("parent_id", sa.String(length=36), nullable=False),
            sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
            sa.Column("push_enabled", sa.Boolean(), nullable=False),
            sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False),
            sa.Column("fee_reminders_enabled", sa.Boolean(), nullable=False),
            sa.Column("preferred_language", sa.String(length=10), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["parent_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id"),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("fee_invoices"):
        op.create_table(
            "fee_invoices",
            sa.Column("student_id", sa.String(length=36), nullable=False),
            sa.Column("invoice_no", sa.String(length=64), nullable=False),
            sa.Column("period_label", sa.String(length=50), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invoice_no"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("fee_invoices"):
        if not _has_index(inspector, "fee_invoices", "ix_fee_invoice_student_due"):
            op.create_index("ix_fee_invoice_student_due", "fee_invoices", ["student_id", "due_date"], unique=False)
        if not _has_index(inspector, "fee_invoices", "ix_fee_invoice_student_status"):
            op.create_index("ix_fee_invoice_student_status", "fee_invoices", ["student_id", "status"], unique=False)

    inspector = sa.inspect(bind)
    if not inspector.has_table("payment_transactions"):
        op.create_table(
            "payment_transactions",
            sa.Column("invoice_id", sa.String(length=36), nullable=False),
            sa.Column("student_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("external_ref", sa.String(length=120), nullable=True),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["invoice_id"], ["fee_invoices.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "external_ref", name="uq_payment_provider_ref"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("payment_transactions"):
        if not _has_index(inspector, "payment_transactions", "ix_payment_student_created"):
            op.create_index("ix_payment_student_created", "payment_transactions", ["student_id", "created_at"], unique=False)
        if not _has_index(inspector, "payment_transactions", "ix_payment_invoice_status"):
            op.create_index("ix_payment_invoice_status", "payment_transactions", ["invoice_id", "status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("payment_transactions"):
        if _has_index(inspector, "payment_transactions", "ix_payment_invoice_status"):
            op.drop_index("ix_payment_invoice_status", table_name="payment_transactions")
        if _has_index(inspector, "payment_transactions", "ix_payment_student_created"):
            op.drop_index("ix_payment_student_created", table_name="payment_transactions")
        op.drop_table("payment_transactions")

    inspector = sa.inspect(bind)
    if inspector.has_table("fee_invoices"):
        if _has_index(inspector, "fee_invoices", "ix_fee_invoice_student_status"):
            op.drop_index("ix_fee_invoice_student_status", table_name="fee_invoices")
        if _has_index(inspector, "fee_invoices", "ix_fee_invoice_student_due"):
            op.drop_index("ix_fee_invoice_student_due", table_name="fee_invoices")
        op.drop_table("fee_invoices")

    inspector = sa.inspect(bind)
    if inspector.has_table("parent_communication_preferences"):
        op.drop_table("parent_communication_preferences")

    inspector = sa.inspect(bind)
    if inspector.has_table("parent_student_links"):
        if _has_index(inspector, "parent_student_links", "ix_parent_link_student_active"):
            op.drop_index("ix_parent_link_student_active", table_name="parent_student_links")
        if _has_index(inspector, "parent_student_links", "ix_parent_link_parent_active"):
            op.drop_index("ix_parent_link_parent_active", table_name="parent_student_links")
        op.drop_table("parent_student_links")

    inspector = sa.inspect(bind)
    if inspector.has_table("parent_profiles"):
        op.drop_table("parent_profiles")
