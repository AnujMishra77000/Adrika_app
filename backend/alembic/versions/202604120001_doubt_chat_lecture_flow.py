"""lecture-linked doubt chat flow

Revision ID: 202604120001
Revises: 202604110004
Create Date: 2026-04-12 12:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604120001"
down_revision = "202604110004"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any((fk.get("name") or "") == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("completed_lectures"):
        op.create_table(
            "completed_lectures",
            sa.Column("teacher_id", sa.CHAR(length=32), nullable=False),
            sa.Column("subject_id", sa.CHAR(length=32), nullable=False),
            sa.Column("batch_id", sa.CHAR(length=32), nullable=True),
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("stream", sa.String(length=20), nullable=False, server_default="common"),
            sa.Column("topic", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.CHAR(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["teacher_id"], ["teacher_profiles.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("completed_lectures"):
        if not _has_index(inspector, "completed_lectures", "ix_completed_lectures_teacher_completed"):
            op.create_index(
                "ix_completed_lectures_teacher_completed",
                "completed_lectures",
                ["teacher_id", "completed_at"],
                unique=False,
            )

        if not _has_index(inspector, "completed_lectures", "ix_completed_lectures_batch_completed"):
            op.create_index(
                "ix_completed_lectures_batch_completed",
                "completed_lectures",
                ["batch_id", "completed_at"],
                unique=False,
            )

        if not _has_index(inspector, "completed_lectures", "ix_completed_lectures_scope_completed"):
            op.create_index(
                "ix_completed_lectures_scope_completed",
                "completed_lectures",
                ["class_level", "stream", "completed_at"],
                unique=False,
            )

        if not _has_index(inspector, "completed_lectures", "ix_completed_lectures_subject_completed"):
            op.create_index(
                "ix_completed_lectures_subject_completed",
                "completed_lectures",
                ["subject_id", "completed_at"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("doubts"):
        columns = {col["name"] for col in inspector.get_columns("doubts")}
        with op.batch_alter_table("doubts") as batch_op:
            if "lecture_id" not in columns:
                batch_op.add_column(sa.Column("lecture_id", sa.CHAR(length=32), nullable=True))
            if "teacher_id" not in columns:
                batch_op.add_column(sa.Column("teacher_id", sa.CHAR(length=32), nullable=True))

        inspector = sa.inspect(bind)
        fk_names = {fk.get("name") or "" for fk in inspector.get_foreign_keys("doubts")}
        with op.batch_alter_table("doubts") as batch_op:
            if "fk_doubts_lecture_id_completed_lectures" not in fk_names:
                batch_op.create_foreign_key(
                    "fk_doubts_lecture_id_completed_lectures",
                    "completed_lectures",
                    ["lecture_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "fk_doubts_teacher_id_teacher_profiles" not in fk_names:
                batch_op.create_foreign_key(
                    "fk_doubts_teacher_id_teacher_profiles",
                    "teacher_profiles",
                    ["teacher_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

        inspector = sa.inspect(bind)
        if not _has_index(inspector, "doubts", "ix_doubt_lecture_created"):
            op.create_index("ix_doubt_lecture_created", "doubts", ["lecture_id", "created_at"], unique=False)

        if not _has_index(inspector, "doubts", "ix_doubt_teacher_status_updated"):
            op.create_index(
                "ix_doubt_teacher_status_updated",
                "doubts",
                ["teacher_id", "status", "updated_at"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("doubts"):
        if _has_index(inspector, "doubts", "ix_doubt_teacher_status_updated"):
            op.drop_index("ix_doubt_teacher_status_updated", table_name="doubts")
        if _has_index(inspector, "doubts", "ix_doubt_lecture_created"):
            op.drop_index("ix_doubt_lecture_created", table_name="doubts")

        inspector = sa.inspect(bind)
        fk_names = {fk.get("name") or "" for fk in inspector.get_foreign_keys("doubts")}
        with op.batch_alter_table("doubts") as batch_op:
            if "fk_doubts_teacher_id_teacher_profiles" in fk_names:
                batch_op.drop_constraint("fk_doubts_teacher_id_teacher_profiles", type_="foreignkey")
            if "fk_doubts_lecture_id_completed_lectures" in fk_names:
                batch_op.drop_constraint("fk_doubts_lecture_id_completed_lectures", type_="foreignkey")

        columns = {col["name"] for col in sa.inspect(bind).get_columns("doubts")}
        with op.batch_alter_table("doubts") as batch_op:
            if "teacher_id" in columns:
                batch_op.drop_column("teacher_id")
            if "lecture_id" in columns:
                batch_op.drop_column("lecture_id")

    inspector = sa.inspect(bind)
    if inspector.has_table("completed_lectures"):
        if _has_index(inspector, "completed_lectures", "ix_completed_lectures_subject_completed"):
            op.drop_index("ix_completed_lectures_subject_completed", table_name="completed_lectures")
        if _has_index(inspector, "completed_lectures", "ix_completed_lectures_scope_completed"):
            op.drop_index("ix_completed_lectures_scope_completed", table_name="completed_lectures")
        if _has_index(inspector, "completed_lectures", "ix_completed_lectures_batch_completed"):
            op.drop_index("ix_completed_lectures_batch_completed", table_name="completed_lectures")
        if _has_index(inspector, "completed_lectures", "ix_completed_lectures_teacher_completed"):
            op.drop_index("ix_completed_lectures_teacher_completed", table_name="completed_lectures")

    inspector = sa.inspect(bind)
    if inspector.has_table("completed_lectures"):
        op.drop_table("completed_lectures")
