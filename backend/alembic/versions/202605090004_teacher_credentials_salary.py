"""add teacher credentials and salary tracking

Revision ID: 202605090004
Revises: 202605090003
Create Date: 2026-05-09 22:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "202605090004"
down_revision = "202605090003"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "teacher_credentials"):
        op.create_table(
            "teacher_credentials",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("login_id", sa.String(length=20), nullable=False),
            sa.Column("password_plain", sa.String(length=128), nullable=False),
            sa.Column("password_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_teacher_credentials_login_id", "teacher_credentials", ["login_id"], unique=False)

    if not _table_exists(inspector, "teacher_salary_profiles"):
        op.create_table(
            "teacher_salary_profiles",
            sa.Column("teacher_id", sa.String(length=36), nullable=False),
            sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["teacher_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("teacher_id"),
        )
        op.create_index("ix_teacher_salary_profiles_teacher", "teacher_salary_profiles", ["teacher_id"], unique=False)

    if not _table_exists(inspector, "teacher_salary_ledgers"):
        op.create_table(
            "teacher_salary_ledgers",
            sa.Column("teacher_id", sa.String(length=36), nullable=False),
            sa.Column("schedule_id", sa.String(length=36), nullable=True),
            sa.Column("completed_lecture_id", sa.String(length=36), nullable=True),
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("stream", sa.String(length=20), nullable=False, server_default="common"),
            sa.Column("subject_id", sa.String(length=36), nullable=True),
            sa.Column("topic", sa.String(length=255), nullable=False),
            sa.Column("lecture_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["teacher_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["schedule_id"], ["lecture_schedules.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["completed_lecture_id"], ["completed_lectures.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("schedule_id"),
            sa.UniqueConstraint("completed_lecture_id"),
        )
        op.create_index("ix_teacher_salary_ledgers_teacher_date", "teacher_salary_ledgers", ["teacher_id", "attendance_date"], unique=False)
        op.create_index("ix_teacher_salary_ledgers_scope_date", "teacher_salary_ledgers", ["class_level", "stream", "attendance_date"], unique=False)

    # widen teaching_scope so multiple class scopes fit
    with op.batch_alter_table("teacher_profiles") as batch_op:
        batch_op.alter_column("teaching_scope", existing_type=sa.String(length=30), type_=sa.String(length=255), existing_nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "teacher_salary_ledgers"):
        op.drop_index("ix_teacher_salary_ledgers_scope_date", table_name="teacher_salary_ledgers")
        op.drop_index("ix_teacher_salary_ledgers_teacher_date", table_name="teacher_salary_ledgers")
        op.drop_table("teacher_salary_ledgers")

    if _table_exists(inspector, "teacher_salary_profiles"):
        op.drop_index("ix_teacher_salary_profiles_teacher", table_name="teacher_salary_profiles")
        op.drop_table("teacher_salary_profiles")

    if _table_exists(inspector, "teacher_credentials"):
        op.drop_index("ix_teacher_credentials_login_id", table_name="teacher_credentials")
        op.drop_table("teacher_credentials")

    with op.batch_alter_table("teacher_profiles") as batch_op:
        batch_op.alter_column("teaching_scope", existing_type=sa.String(length=255), type_=sa.String(length=30), existing_nullable=True)
