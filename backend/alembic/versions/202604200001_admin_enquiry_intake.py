"""admin enquiry intake table

Revision ID: 202604200001
Revises: 202604190001
Create Date: 2026-04-20 14:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604200001"
down_revision = "202604190001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "student_enquiries"):
        op.create_table(
            "student_enquiries",
            sa.Column("student_name", sa.String(length=255), nullable=False),
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("previous_class", sa.String(length=50), nullable=True),
            sa.Column("previous_percentage", sa.Numeric(5, 2), nullable=True),
            sa.Column("school_name", sa.String(length=255), nullable=True),
            sa.Column("language", sa.String(length=20), nullable=False, server_default="english"),
            sa.Column("contact_number", sa.String(length=20), nullable=False),
            sa.Column("parent_contact_number", sa.String(length=20), nullable=False),
            sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("fee_class_level", sa.Integer(), nullable=False),
            sa.Column("fee_stream", sa.String(length=20), nullable=True),
            sa.Column("fee_structure_id", sa.Uuid(as_uuid=False), sa.ForeignKey("fee_structures.id", ondelete="SET NULL"), nullable=True),
            sa.Column("fee_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("negotiable_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("installment_count", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="follow_up"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("class_level IN (10, 11, 12)", name="ck_student_enquiry_class_level"),
            sa.CheckConstraint("fee_class_level IN (10, 11, 12)", name="ck_student_enquiry_fee_class_level"),
            sa.CheckConstraint("fee_stream IS NULL OR fee_stream IN ('science', 'commerce')", name="ck_student_enquiry_fee_stream"),
            sa.CheckConstraint("language IN ('hindi', 'english')", name="ck_student_enquiry_language"),
            sa.CheckConstraint(
                "status IN ('interested', 'follow_up', 'confirmed', 'not_interested')",
                name="ck_student_enquiry_status",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "student_enquiries") and not _index_exists(
        inspector, "student_enquiries", "ix_student_enquiry_status_followup"
    ):
        op.create_index(
            "ix_student_enquiry_status_followup",
            "student_enquiries",
            ["status", "follow_up_at"],
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "student_enquiries") and not _index_exists(
        inspector, "student_enquiries", "ix_student_enquiry_class_stream"
    ):
        op.create_index(
            "ix_student_enquiry_class_stream",
            "student_enquiries",
            ["class_level", "fee_stream"],
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "student_enquiries") and not _index_exists(
        inspector, "student_enquiries", "ix_student_enquiry_contact"
    ):
        op.create_index(
            "ix_student_enquiry_contact",
            "student_enquiries",
            ["contact_number", "parent_contact_number"],
        )


def downgrade() -> None:
    # Intentionally non-destructive for production safety.
    pass
