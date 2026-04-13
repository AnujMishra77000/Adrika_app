"""homework timing, attachments, and read tracking

Revision ID: 202604110001
Revises: 202604100004
Create Date: 2026-04-11 09:40:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604110001"
down_revision = "202604100004"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def _backfill_homework_timing(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE homework
                SET due_at = COALESCE(due_at, (due_date::text || ' 23:59:00+00')::timestamptz)
                WHERE due_date IS NOT NULL
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE homework
                SET publish_at = COALESCE(publish_at, created_at)
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE homework
                SET expires_at = COALESCE(expires_at, due_at + interval '24 hours')
                WHERE due_at IS NOT NULL
                """
            )
        )
        return

    # SQLite and other development dialects.
    op.execute(
        sa.text(
            """
            UPDATE homework
            SET due_at = COALESCE(due_at, datetime(due_date || ' 23:59:00'))
            WHERE due_date IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE homework
            SET publish_at = COALESCE(publish_at, created_at)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE homework
            SET expires_at = COALESCE(expires_at, datetime(due_at, '+24 hours'))
            WHERE due_at IS NOT NULL
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("homework"):
        if not _has_column(inspector, "homework", "due_at"):
            op.add_column("homework", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column(inspector, "homework", "publish_at"):
            op.add_column("homework", sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column(inspector, "homework", "expires_at"):
            op.add_column("homework", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(bind)
    if inspector.has_table("homework"):
        _backfill_homework_timing(bind)

    inspector = sa.inspect(bind)
    if inspector.has_table("homework") and not _has_index(inspector, "homework", "ix_homework_due_at"):
        op.create_index("ix_homework_due_at", "homework", ["due_at"], unique=False)

    if inspector.has_table("homework") and not _has_index(inspector, "homework", "ix_homework_status_expires"):
        op.create_index("ix_homework_status_expires", "homework", ["status", "expires_at"], unique=False)

    if not inspector.has_table("homework_attachments"):
        op.create_table(
            "homework_attachments",
            sa.Column("homework_id", sa.String(length=36), nullable=False),
            sa.Column("attachment_type", sa.String(length=16), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("storage_path", sa.String(length=1024), nullable=False),
            sa.Column("file_url", sa.String(length=1024), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("is_generated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["homework_id"], ["homework.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("homework_attachments") and not _has_index(
        inspector,
        "homework_attachments",
        "ix_homework_attachments_homework",
    ):
        op.create_index(
            "ix_homework_attachments_homework",
            "homework_attachments",
            ["homework_id"],
            unique=False,
        )

    if inspector.has_table("homework_attachments") and not _has_index(
        inspector,
        "homework_attachments",
        "ix_homework_attachments_homework_created",
    ):
        op.create_index(
            "ix_homework_attachments_homework_created",
            "homework_attachments",
            ["homework_id", "created_at"],
            unique=False,
        )

    if not inspector.has_table("homework_reads"):
        op.create_table(
            "homework_reads",
            sa.Column("homework_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["homework_id"], ["homework.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("homework_id", "user_id", name="uq_homework_read"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("homework_reads") and not _has_index(
        inspector,
        "homework_reads",
        "ix_homework_reads_user_read",
    ):
        op.create_index(
            "ix_homework_reads_user_read",
            "homework_reads",
            ["user_id", "read_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("homework_reads"):
        if _has_index(inspector, "homework_reads", "ix_homework_reads_user_read"):
            op.drop_index("ix_homework_reads_user_read", table_name="homework_reads")
        op.drop_table("homework_reads")

    inspector = sa.inspect(bind)
    if inspector.has_table("homework_attachments"):
        if _has_index(inspector, "homework_attachments", "ix_homework_attachments_homework_created"):
            op.drop_index("ix_homework_attachments_homework_created", table_name="homework_attachments")
        if _has_index(inspector, "homework_attachments", "ix_homework_attachments_homework"):
            op.drop_index("ix_homework_attachments_homework", table_name="homework_attachments")
        op.drop_table("homework_attachments")

    inspector = sa.inspect(bind)
    if inspector.has_table("homework"):
        if _has_index(inspector, "homework", "ix_homework_status_expires"):
            op.drop_index("ix_homework_status_expires", table_name="homework")
        if _has_index(inspector, "homework", "ix_homework_due_at"):
            op.drop_index("ix_homework_due_at", table_name="homework")

        columns = {column.get("name") for column in inspector.get_columns("homework")}
        with op.batch_alter_table("homework") as batch_op:
            if "expires_at" in columns:
                batch_op.drop_column("expires_at")
            if "publish_at" in columns:
                batch_op.drop_column("publish_at")
            if "due_at" in columns:
                batch_op.drop_column("due_at")
