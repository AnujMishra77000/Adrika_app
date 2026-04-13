"""student fee structure assignments

Revision ID: 202604100003
Revises: 202604100002
Create Date: 2026-04-10 17:05:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604100003"
down_revision = "202604100002"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("student_fee_structure_assignments"):
        op.create_table(
            "student_fee_structure_assignments",
            sa.Column("student_id", sa.String(length=36), nullable=False),
            sa.Column("fee_structure_id", sa.String(length=36), nullable=False),
            sa.Column("assigned_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["fee_structure_id"], ["fee_structures.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("student_id", name="uq_student_fee_assignment_student"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("student_fee_structure_assignments") and not _has_index(
        inspector,
        "student_fee_structure_assignments",
        "ix_student_fee_assignment_structure_active",
    ):
        op.create_index(
            "ix_student_fee_assignment_structure_active",
            "student_fee_structure_assignments",
            ["fee_structure_id", "is_active"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("student_fee_structure_assignments"):
        if _has_index(
            inspector,
            "student_fee_structure_assignments",
            "ix_student_fee_assignment_structure_active",
        ):
            op.drop_index(
                "ix_student_fee_assignment_structure_active",
                table_name="student_fee_structure_assignments",
            )
        op.drop_table("student_fee_structure_assignments")
