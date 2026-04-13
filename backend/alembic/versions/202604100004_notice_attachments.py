"""notice attachments and extended targets

Revision ID: 202604100004
Revises: 202604100003
Create Date: 2026-04-10 20:35:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604100004"
down_revision = "202604100003"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("notice_attachments"):
        op.create_table(
            "notice_attachments",
            sa.Column("notice_id", sa.String(length=36), nullable=False),
            sa.Column("attachment_type", sa.String(length=16), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("storage_path", sa.String(length=1024), nullable=False),
            sa.Column("file_url", sa.String(length=1024), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("image_width", sa.Integer(), nullable=True),
            sa.Column("image_height", sa.Integer(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["notice_id"], ["notices.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("notice_attachments") and not _has_index(
        inspector,
        "notice_attachments",
        "ix_notice_attachments_notice",
    ):
        op.create_index(
            "ix_notice_attachments_notice",
            "notice_attachments",
            ["notice_id"],
            unique=False,
        )

    if inspector.has_table("notice_attachments") and not _has_index(
        inspector,
        "notice_attachments",
        "ix_notice_attachments_notice_created",
    ):
        op.create_index(
            "ix_notice_attachments_notice_created",
            "notice_attachments",
            ["notice_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("notice_attachments"):
        if _has_index(inspector, "notice_attachments", "ix_notice_attachments_notice_created"):
            op.drop_index("ix_notice_attachments_notice_created", table_name="notice_attachments")
        if _has_index(inspector, "notice_attachments", "ix_notice_attachments_notice"):
            op.drop_index("ix_notice_attachments_notice", table_name="notice_attachments")
        op.drop_table("notice_attachments")
