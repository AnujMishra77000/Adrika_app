"""notification realtime infrastructure

Revision ID: 202604190001
Revises: 202604130002
Create Date: 2026-04-19 11:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202604190001"
down_revision = "202604130002"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "device_registrations"):
        op.create_table(
            "device_registrations",
            sa.Column("user_id", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("platform", sa.String(length=20), nullable=False),
            sa.Column("device_id", sa.String(length=255), nullable=False),
            sa.Column("push_token", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("push_token", name="uq_device_registrations_push_token"),
        )
        op.create_index("ix_device_reg_user_active", "device_registrations", ["user_id", "is_active"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("recipient_user_id", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "notification_type",
                sa.Enum(
                    "notice",
                    "homework",
                    "test",
                    "result",
                    "doubt",
                    "system",
                    name="notification_type",
                    native_enum=False,
                ),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "notifications") and not _column_exists(inspector, "notifications", "metadata"):
        op.add_column("notifications", sa.Column("metadata", sa.JSON(), nullable=True))
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "notifications") and not _index_exists(
        inspector,
        "notifications",
        "ix_notifications_user_read_created",
    ):
        op.create_index(
            "ix_notifications_user_read_created",
            "notifications",
            ["recipient_user_id", "is_read", "created_at"],
        )

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "notification_deliveries"):
        op.create_table(
            "notification_deliveries",
            sa.Column(
                "notification_id",
                sa.Uuid(as_uuid=False),
                sa.ForeignKey("notifications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "channel",
                sa.Enum("in_app", "push", "whatsapp", name="delivery_channel", native_enum=False),
                nullable=False,
            ),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("provider_response", sa.Text(), nullable=True),
            sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("channel", "provider_message_id", name="uq_channel_provider_message"),
        )
        op.create_index(
            "ix_notification_delivery_channel_status_created",
            "notification_deliveries",
            ["channel", "status", "created_at"],
        )


def downgrade() -> None:
    # Intentionally non-destructive for production safety.
    pass
