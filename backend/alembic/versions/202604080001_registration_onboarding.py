"""add registration requests and extended student/teacher profile fields

Revision ID: 202604080001
Revises: 202604070003
Create Date: 2026-04-08 12:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604080001"
down_revision = "202604070003"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("student_profiles"):
        if not _has_column(inspector, "student_profiles", "class_name"):
            op.add_column("student_profiles", sa.Column("class_name", sa.String(length=50), nullable=True))
        if not _has_column(inspector, "student_profiles", "stream"):
            op.add_column("student_profiles", sa.Column("stream", sa.String(length=20), nullable=True))
        if not _has_column(inspector, "student_profiles", "parent_contact_number"):
            op.add_column("student_profiles", sa.Column("parent_contact_number", sa.String(length=20), nullable=True))
        if not _has_column(inspector, "student_profiles", "address"):
            op.add_column("student_profiles", sa.Column("address", sa.String(length=500), nullable=True))
        if not _has_column(inspector, "student_profiles", "school_details"):
            op.add_column("student_profiles", sa.Column("school_details", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "student_profiles", "photo_url"):
            op.add_column("student_profiles", sa.Column("photo_url", sa.String(length=1024), nullable=True))

    inspector = sa.inspect(bind)
    if inspector.has_table("teacher_profiles"):
        if not _has_column(inspector, "teacher_profiles", "age"):
            op.add_column("teacher_profiles", sa.Column("age", sa.Integer(), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "gender"):
            op.add_column("teacher_profiles", sa.Column("gender", sa.String(length=20), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "qualification"):
            op.add_column("teacher_profiles", sa.Column("qualification", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "specialization"):
            op.add_column("teacher_profiles", sa.Column("specialization", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "school_college"):
            op.add_column("teacher_profiles", sa.Column("school_college", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "address"):
            op.add_column("teacher_profiles", sa.Column("address", sa.String(length=500), nullable=True))
        if not _has_column(inspector, "teacher_profiles", "photo_url"):
            op.add_column("teacher_profiles", sa.Column("photo_url", sa.String(length=1024), nullable=True))

    inspector = sa.inspect(bind)
    if not inspector.has_table("registration_requests"):
        op.create_table(
            "registration_requests",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("requested_role", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("registration_requests"):
        if not _has_index(inspector, "registration_requests", "ix_registration_requests_status_role_created"):
            op.create_index(
                "ix_registration_requests_status_role_created",
                "registration_requests",
                ["status", "requested_role", "created_at"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("registration_requests"):
        if _has_index(inspector, "registration_requests", "ix_registration_requests_status_role_created"):
            op.drop_index("ix_registration_requests_status_role_created", table_name="registration_requests")
        op.drop_table("registration_requests")

    inspector = sa.inspect(bind)
    if inspector.has_table("teacher_profiles"):
        if _has_column(inspector, "teacher_profiles", "photo_url"):
            op.drop_column("teacher_profiles", "photo_url")
        if _has_column(inspector, "teacher_profiles", "address"):
            op.drop_column("teacher_profiles", "address")
        if _has_column(inspector, "teacher_profiles", "school_college"):
            op.drop_column("teacher_profiles", "school_college")
        if _has_column(inspector, "teacher_profiles", "specialization"):
            op.drop_column("teacher_profiles", "specialization")
        if _has_column(inspector, "teacher_profiles", "qualification"):
            op.drop_column("teacher_profiles", "qualification")
        if _has_column(inspector, "teacher_profiles", "gender"):
            op.drop_column("teacher_profiles", "gender")
        if _has_column(inspector, "teacher_profiles", "age"):
            op.drop_column("teacher_profiles", "age")

    inspector = sa.inspect(bind)
    if inspector.has_table("student_profiles"):
        if _has_column(inspector, "student_profiles", "photo_url"):
            op.drop_column("student_profiles", "photo_url")
        if _has_column(inspector, "student_profiles", "school_details"):
            op.drop_column("student_profiles", "school_details")
        if _has_column(inspector, "student_profiles", "address"):
            op.drop_column("student_profiles", "address")
        if _has_column(inspector, "student_profiles", "parent_contact_number"):
            op.drop_column("student_profiles", "parent_contact_number")
        if _has_column(inspector, "student_profiles", "stream"):
            op.drop_column("student_profiles", "stream")
        if _has_column(inspector, "student_profiles", "class_name"):
            op.drop_column("student_profiles", "class_name")
