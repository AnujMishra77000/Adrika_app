"""admin lecture schedules with done bridge

Revision ID: 202604130001
Revises: 202604120001
Create Date: 2026-04-13 10:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604130001"
down_revision = "202604120001"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any((fk.get("name") or "") == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("lecture_schedules"):
        op.create_table(
            "lecture_schedules",
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("stream", sa.String(length=20), nullable=False, server_default="common"),
            sa.Column("subject_id", sa.CHAR(length=32), nullable=False),
            sa.Column("teacher_id", sa.CHAR(length=32), nullable=False),
            sa.Column("batch_id", sa.CHAR(length=32), nullable=True),
            sa.Column("topic", sa.String(length=255), nullable=False),
            sa.Column("lecture_notes", sa.Text(), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
            sa.Column("all_students_in_scope", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_by_user_id", sa.CHAR(length=32), nullable=True),
            sa.Column("completed_by_user_id", sa.CHAR(length=32), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["teacher_id"], ["teacher_profiles.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("lecture_schedules"):
        if not _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_status_scheduled"):
            op.create_index(
                "ix_lecture_schedules_status_scheduled",
                "lecture_schedules",
                ["status", "scheduled_at"],
                unique=False,
            )
        if not _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_scope_scheduled"):
            op.create_index(
                "ix_lecture_schedules_scope_scheduled",
                "lecture_schedules",
                ["class_level", "stream", "scheduled_at"],
                unique=False,
            )
        if not _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_teacher_scheduled"):
            op.create_index(
                "ix_lecture_schedules_teacher_scheduled",
                "lecture_schedules",
                ["teacher_id", "scheduled_at"],
                unique=False,
            )
        if not _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_subject_scheduled"):
            op.create_index(
                "ix_lecture_schedules_subject_scheduled",
                "lecture_schedules",
                ["subject_id", "scheduled_at"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table("lecture_schedule_students"):
        op.create_table(
            "lecture_schedule_students",
            sa.Column("lecture_schedule_id", sa.CHAR(length=32), nullable=False),
            sa.Column("student_id", sa.CHAR(length=32), nullable=False),
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
            sa.ForeignKeyConstraint(["lecture_schedule_id"], ["lecture_schedules.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lecture_schedule_id", "student_id", name="uq_lecture_schedule_student"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("lecture_schedule_students"):
        if not _has_index(inspector, "lecture_schedule_students", "ix_lecture_schedule_students_schedule"):
            op.create_index(
                "ix_lecture_schedule_students_schedule",
                "lecture_schedule_students",
                ["lecture_schedule_id"],
                unique=False,
            )
        if not _has_index(inspector, "lecture_schedule_students", "ix_lecture_schedule_students_student"):
            op.create_index(
                "ix_lecture_schedule_students_student",
                "lecture_schedule_students",
                ["student_id"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("completed_lectures"):
        columns = {col["name"] for col in inspector.get_columns("completed_lectures")}
        with op.batch_alter_table("completed_lectures") as batch_op:
            if "schedule_id" not in columns:
                batch_op.add_column(sa.Column("schedule_id", sa.CHAR(length=32), nullable=True))

        inspector = sa.inspect(bind)
        if not _has_fk(inspector, "completed_lectures", "fk_completed_lectures_schedule_id_lecture_schedules"):
            with op.batch_alter_table("completed_lectures") as batch_op:
                batch_op.create_foreign_key(
                    "fk_completed_lectures_schedule_id_lecture_schedules",
                    "lecture_schedules",
                    ["schedule_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

        inspector = sa.inspect(bind)
        if not _has_index(inspector, "completed_lectures", "ix_completed_lectures_schedule"):
            op.create_index(
                "ix_completed_lectures_schedule",
                "completed_lectures",
                ["schedule_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("completed_lectures"):
        if _has_index(inspector, "completed_lectures", "ix_completed_lectures_schedule"):
            op.drop_index("ix_completed_lectures_schedule", table_name="completed_lectures")

        inspector = sa.inspect(bind)
        if _has_fk(inspector, "completed_lectures", "fk_completed_lectures_schedule_id_lecture_schedules"):
            with op.batch_alter_table("completed_lectures") as batch_op:
                batch_op.drop_constraint(
                    "fk_completed_lectures_schedule_id_lecture_schedules",
                    type_="foreignkey",
                )

        columns = {col["name"] for col in sa.inspect(bind).get_columns("completed_lectures")}
        if "schedule_id" in columns:
            with op.batch_alter_table("completed_lectures") as batch_op:
                batch_op.drop_column("schedule_id")

    inspector = sa.inspect(bind)
    if inspector.has_table("lecture_schedule_students"):
        if _has_index(inspector, "lecture_schedule_students", "ix_lecture_schedule_students_student"):
            op.drop_index("ix_lecture_schedule_students_student", table_name="lecture_schedule_students")
        if _has_index(inspector, "lecture_schedule_students", "ix_lecture_schedule_students_schedule"):
            op.drop_index("ix_lecture_schedule_students_schedule", table_name="lecture_schedule_students")
        op.drop_table("lecture_schedule_students")

    inspector = sa.inspect(bind)
    if inspector.has_table("lecture_schedules"):
        if _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_subject_scheduled"):
            op.drop_index("ix_lecture_schedules_subject_scheduled", table_name="lecture_schedules")
        if _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_teacher_scheduled"):
            op.drop_index("ix_lecture_schedules_teacher_scheduled", table_name="lecture_schedules")
        if _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_scope_scheduled"):
            op.drop_index("ix_lecture_schedules_scope_scheduled", table_name="lecture_schedules")
        if _has_index(inspector, "lecture_schedules", "ix_lecture_schedules_status_scheduled"):
            op.drop_index("ix_lecture_schedules_status_scheduled", table_name="lecture_schedules")
        op.drop_table("lecture_schedules")
