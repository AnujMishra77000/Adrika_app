"""homework submissions and completion tracking

Revision ID: 202604110002
Revises: 202604110001
Create Date: 2026-04-11 21:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604110002"
down_revision = "202604110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homework_submissions",
        sa.Column("homework_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("submitted", "late", name="homework_submission_status", native_enum=False),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["homework_id"], ["homework.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("homework_id", "student_id", name="uq_homework_submission_student"),
    )
    op.create_index(
        "ix_homework_submissions_student_status",
        "homework_submissions",
        ["student_id", "status", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "ix_homework_submissions_homework_status",
        "homework_submissions",
        ["homework_id", "status"],
        unique=False,
    )

    op.create_table(
        "homework_submission_attachments",
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["homework_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_homework_submission_attachments_submission",
        "homework_submission_attachments",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        "ix_homework_submission_attachments_submission_created",
        "homework_submission_attachments",
        ["submission_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_homework_submission_attachments_submission_created",
        table_name="homework_submission_attachments",
    )
    op.drop_index(
        "ix_homework_submission_attachments_submission",
        table_name="homework_submission_attachments",
    )
    op.drop_table("homework_submission_attachments")

    op.drop_index(
        "ix_homework_submissions_homework_status",
        table_name="homework_submissions",
    )
    op.drop_index(
        "ix_homework_submissions_student_status",
        table_name="homework_submissions",
    )
    op.drop_table("homework_submissions")
