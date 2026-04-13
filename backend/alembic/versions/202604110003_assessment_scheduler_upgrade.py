"""assessment scheduler and question bank enhancement

Revision ID: 202604110003
Revises: 202604110002
Create Date: 2026-04-11 23:55:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604110003"
down_revision = "202604110002"
branch_labels = None
depends_on = None


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("assessments"):
        existing = _columns(inspector, "assessments")
        with op.batch_alter_table("assessments") as batch:
            if "class_level" not in existing:
                batch.add_column(sa.Column("class_level", sa.Integer(), nullable=True))
            if "stream" not in existing:
                batch.add_column(sa.Column("stream", sa.String(length=20), nullable=True))
            if "topic" not in existing:
                batch.add_column(sa.Column("topic", sa.String(length=150), nullable=True))
            if "passing_marks" not in existing:
                batch.add_column(
                    sa.Column(
                        "passing_marks",
                        sa.Numeric(8, 2),
                        nullable=False,
                        server_default="0",
                    )
                )

    inspector = sa.inspect(bind)
    if inspector.has_table("assessments") and not _has_index(inspector, "assessments", "ix_assessment_academic_scope"):
        op.create_index(
            "ix_assessment_academic_scope",
            "assessments",
            ["class_level", "stream", "subject_id"],
            unique=False,
        )

    if inspector.has_table("assessments") and not _has_index(inspector, "assessments", "ix_assessment_status_window"):
        op.create_index(
            "ix_assessment_status_window",
            "assessments",
            ["status", "starts_at", "ends_at"],
            unique=False,
        )

    if inspector.has_table("question_bank"):
        existing = _columns(inspector, "question_bank")
        with op.batch_alter_table("question_bank") as batch:
            if "class_level" not in existing:
                batch.add_column(sa.Column("class_level", sa.Integer(), nullable=True))
            if "stream" not in existing:
                batch.add_column(sa.Column("stream", sa.String(length=20), nullable=True))
            if "topic" not in existing:
                batch.add_column(sa.Column("topic", sa.String(length=150), nullable=True))
            if "default_marks" not in existing:
                batch.add_column(
                    sa.Column(
                        "default_marks",
                        sa.Numeric(8, 2),
                        nullable=False,
                        server_default="1",
                    )
                )

    inspector = sa.inspect(bind)
    if inspector.has_table("question_bank") and not _has_index(inspector, "question_bank", "ix_question_bank_scope"):
        op.create_index(
            "ix_question_bank_scope",
            "question_bank",
            ["class_level", "stream", "subject_id", "is_active"],
            unique=False,
        )

    if inspector.has_table("question_bank") and not _has_index(inspector, "question_bank", "ix_question_bank_topic"):
        op.create_index(
            "ix_question_bank_topic",
            "question_bank",
            ["topic"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("question_bank") and _has_index(inspector, "question_bank", "ix_question_bank_topic"):
        op.drop_index("ix_question_bank_topic", table_name="question_bank")
    if inspector.has_table("question_bank") and _has_index(inspector, "question_bank", "ix_question_bank_scope"):
        op.drop_index("ix_question_bank_scope", table_name="question_bank")

    inspector = sa.inspect(bind)
    if inspector.has_table("question_bank"):
        existing = _columns(inspector, "question_bank")
        with op.batch_alter_table("question_bank") as batch:
            if "default_marks" in existing:
                batch.drop_column("default_marks")
            if "topic" in existing:
                batch.drop_column("topic")
            if "stream" in existing:
                batch.drop_column("stream")
            if "class_level" in existing:
                batch.drop_column("class_level")

    inspector = sa.inspect(bind)
    if inspector.has_table("assessments") and _has_index(inspector, "assessments", "ix_assessment_status_window"):
        op.drop_index("ix_assessment_status_window", table_name="assessments")
    if inspector.has_table("assessments") and _has_index(inspector, "assessments", "ix_assessment_academic_scope"):
        op.drop_index("ix_assessment_academic_scope", table_name="assessments")

    inspector = sa.inspect(bind)
    if inspector.has_table("assessments"):
        existing = _columns(inspector, "assessments")
        with op.batch_alter_table("assessments") as batch:
            if "passing_marks" in existing:
                batch.drop_column("passing_marks")
            if "topic" in existing:
                batch.drop_column("topic")
            if "stream" in existing:
                batch.drop_column("stream")
            if "class_level" in existing:
                batch.drop_column("class_level")
