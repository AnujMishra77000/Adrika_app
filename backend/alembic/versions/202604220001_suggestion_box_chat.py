"""add suggestion box chat tables

Revision ID: 202604220001
Revises: 202604200004
Create Date: 2026-04-22 17:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604220001"
down_revision = "202604200004"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _constraint_exists(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(constraint.get("name") == constraint_name for constraint in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "suggestion_threads"):
        op.create_table(
            "suggestion_threads",
            sa.Column("student_id", sa.String(length=36), nullable=False),
            sa.Column("student_user_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_sender_user_id", sa.String(length=36), nullable=True),
            sa.Column("admin_last_read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("student_last_read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["last_sender_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("student_id", name="uq_suggestion_thread_student"),
        )

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "suggestion_messages"):
        op.create_table(
            "suggestion_messages",
            sa.Column("thread_id", sa.String(length=36), nullable=False),
            sa.Column("sender_user_id", sa.String(length=36), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["thread_id"], ["suggestion_threads.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "suggestion_threads"):
        if not _constraint_exists(inspector, "suggestion_threads", "uq_suggestion_thread_student"):
            with op.batch_alter_table("suggestion_threads") as batch_op:
                batch_op.create_unique_constraint("uq_suggestion_thread_student", ["student_id"])

        if not _index_exists(inspector, "suggestion_threads", "ix_suggestion_threads_last_message"):
            op.create_index(
                "ix_suggestion_threads_last_message",
                "suggestion_threads",
                ["last_message_at"],
                unique=False,
            )
        if not _index_exists(inspector, "suggestion_threads", "ix_suggestion_threads_student"):
            op.create_index(
                "ix_suggestion_threads_student",
                "suggestion_threads",
                ["student_id"],
                unique=False,
            )
        if not _index_exists(inspector, "suggestion_threads", "ix_suggestion_threads_admin_read"):
            op.create_index(
                "ix_suggestion_threads_admin_read",
                "suggestion_threads",
                ["admin_last_read_at", "last_message_at"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "suggestion_messages") and not _index_exists(
        inspector,
        "suggestion_messages",
        "ix_suggestion_messages_thread_created",
    ):
        op.create_index(
            "ix_suggestion_messages_thread_created",
            "suggestion_messages",
            ["thread_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    # Non-destructive downgrade strategy by design.
    pass
