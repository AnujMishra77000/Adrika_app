"""add teacher batch assignments

Revision ID: 202604070002
Revises: 202604070001
Create Date: 2026-04-07 10:40:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604070002"
down_revision = "202604070001"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("teacher_batch_assignments"):
        op.create_table(
            "teacher_batch_assignments",
            sa.Column("teacher_id", sa.String(length=36), nullable=False),
            sa.Column("batch_id", sa.String(length=36), nullable=False),
            sa.Column("subject_id", sa.String(length=36), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["teacher_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("teacher_id", "batch_id", "subject_id", name="uq_teacher_batch_subject"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("teacher_batch_assignments"):
        if not _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_teacher"):
            op.create_index(
                "ix_teacher_assignment_teacher",
                "teacher_batch_assignments",
                ["teacher_id"],
                unique=False,
            )
        if not _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_batch"):
            op.create_index(
                "ix_teacher_assignment_batch",
                "teacher_batch_assignments",
                ["batch_id"],
                unique=False,
            )
        if not _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_subject"):
            op.create_index(
                "ix_teacher_assignment_subject",
                "teacher_batch_assignments",
                ["subject_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("teacher_batch_assignments"):
        if _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_subject"):
            op.drop_index("ix_teacher_assignment_subject", table_name="teacher_batch_assignments")
        if _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_batch"):
            op.drop_index("ix_teacher_assignment_batch", table_name="teacher_batch_assignments")
        if _has_index(inspector, "teacher_batch_assignments", "ix_teacher_assignment_teacher"):
            op.drop_index("ix_teacher_assignment_teacher", table_name="teacher_batch_assignments")
        op.drop_table("teacher_batch_assignments")
