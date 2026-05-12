"""add teacher teaching scope field

Revision ID: 202604130002
Revises: 202604130001
Create Date: 2026-04-13 15:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604130002"
down_revision = "202604130001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("teacher_profiles"):
        columns = {column["name"] for column in inspector.get_columns("teacher_profiles")}
        if "teaching_scope" not in columns:
            with op.batch_alter_table("teacher_profiles") as batch_op:
                batch_op.add_column(sa.Column("teaching_scope", sa.String(length=30), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("teacher_profiles"):
        columns = {column["name"] for column in inspector.get_columns("teacher_profiles")}
        if "teaching_scope" in columns:
            with op.batch_alter_table("teacher_profiles") as batch_op:
                batch_op.drop_column("teaching_scope")
