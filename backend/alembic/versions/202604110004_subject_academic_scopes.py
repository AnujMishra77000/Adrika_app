"""subject academic scopes for dynamic assessment subjects

Revision ID: 202604110004
Revises: 202604110003
Create Date: 2026-04-12 02:10:00
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202604110004"
down_revision = "202604110003"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _fetch_subject_id(bind, *, code: str, name: str, fallback_codes: list[str] | None = None) -> str:
    codes = [code.strip().upper()]
    for item in fallback_codes or []:
        normalized = item.strip().upper()
        if normalized and normalized not in codes:
            codes.append(normalized)

    for candidate in codes:
        row = bind.execute(
            sa.text("SELECT id FROM subjects WHERE UPPER(code) = :code LIMIT 1"),
            {"code": candidate},
        ).first()
        if row:
            return row[0]

    row = bind.execute(
        sa.text("SELECT id FROM subjects WHERE LOWER(name) = :name LIMIT 1"),
        {"name": name.strip().lower()},
    ).first()
    if row:
        return row[0]

    now = datetime.now(timezone.utc)
    subject_id = uuid4().hex
    bind.execute(
        sa.text(
            """
            INSERT INTO subjects (id, code, name, created_at, updated_at)
            VALUES (:id, :code, :name, :created_at, :updated_at)
            """
        ),
        {
            "id": subject_id,
            "code": code.strip().upper(),
            "name": name.strip(),
            "created_at": now,
            "updated_at": now,
        },
    )
    return subject_id


def _ensure_scope(bind, *, subject_id: str, class_level: int, stream: str) -> None:
    existing = bind.execute(
        sa.text(
            """
            SELECT id
            FROM subject_academic_scopes
            WHERE subject_id = :subject_id
              AND class_level = :class_level
              AND stream = :stream
            LIMIT 1
            """
        ),
        {
            "subject_id": subject_id,
            "class_level": class_level,
            "stream": stream,
        },
    ).first()
    if existing:
        return

    now = datetime.now(timezone.utc)
    bind.execute(
        sa.text(
            """
            INSERT INTO subject_academic_scopes (id, subject_id, class_level, stream, created_at, updated_at)
            VALUES (:id, :subject_id, :class_level, :stream, :created_at, :updated_at)
            """
        ),
        {
            "id": uuid4().hex,
            "subject_id": subject_id,
            "class_level": class_level,
            "stream": stream,
            "created_at": now,
            "updated_at": now,
        },
    )


def _seed_default_scopes(bind) -> None:
    # 10th, 11th Science/Commerce, 12th Science/Commerce defaults.
    curriculum = {
        "English": {
            "code": "ENGLISH",
            "scopes": [(10, "common"), (11, "science"), (11, "commerce"), (12, "science"), (12, "commerce")],
        },
        "Hindi": {
            "code": "HINDI",
            "scopes": [(10, "common"), (11, "science"), (11, "commerce"), (12, "science"), (12, "commerce")],
        },
        "Marathi": {
            "code": "MARATHI",
            "scopes": [(10, "common")],
        },
        "Mathematics": {
            "code": "MATHEMATICS",
            "fallback_codes": ["MATH"],
            "scopes": [(10, "common"), (11, "science"), (12, "science")],
        },
        "Science": {
            "code": "SCIENCE",
            "fallback_codes": ["SCI"],
            "scopes": [(10, "common")],
        },
        "Social Science": {
            "code": "SOCIAL_SCIENCE",
            "scopes": [(10, "common")],
        },
        "Geography": {
            "code": "GEOGRAPHY",
            "scopes": [(10, "common")],
        },
        "History": {
            "code": "HISTORY",
            "scopes": [(10, "common")],
        },
        "Economics": {
            "code": "ECONOMICS",
            "scopes": [(10, "common"), (11, "commerce"), (12, "commerce")],
        },
        "Algebra": {
            "code": "ALGEBRA",
            "scopes": [(11, "science")],
        },
        "Geometry": {
            "code": "GEOMETRY",
            "scopes": [(11, "science")],
        },
        "Physics": {
            "code": "PHYSICS",
            "scopes": [(11, "science"), (12, "science")],
        },
        "Chemistry": {
            "code": "CHEMISTRY",
            "scopes": [(11, "science"), (12, "science")],
        },
        "Biology": {
            "code": "BIOLOGY",
            "scopes": [(11, "science"), (12, "science")],
        },
        "Book Keeping & Accountancy": {
            "code": "BK_ACCOUNTANCY",
            "scopes": [(11, "commerce"), (12, "commerce")],
        },
        "Organization of Commerce": {
            "code": "ORG_COMMERCE",
            "scopes": [(11, "commerce"), (12, "commerce")],
        },
        "Secretarial Practice": {
            "code": "SECRETARIAL_PRACTICE",
            "scopes": [(11, "commerce"), (12, "commerce")],
        },
        "Mathematics & Statistics": {
            "code": "MATH_STATS",
            "scopes": [(11, "commerce"), (12, "commerce")],
        },
    }

    for name, config in curriculum.items():
        subject_id = _fetch_subject_id(
            bind,
            code=config["code"],
            name=name,
            fallback_codes=config.get("fallback_codes", []),
        )
        for class_level, stream in config["scopes"]:
            _ensure_scope(bind, subject_id=subject_id, class_level=class_level, stream=stream)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("subject_academic_scopes"):
        op.create_table(
            "subject_academic_scopes",
            sa.Column("subject_id", sa.CHAR(length=32), nullable=False),
            sa.Column("class_level", sa.Integer(), nullable=False),
            sa.Column("stream", sa.String(length=20), nullable=False, server_default="common"),
            sa.Column("id", sa.CHAR(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("subject_id", "class_level", "stream", name="uq_subject_scope"),
        )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "subject_academic_scopes", "ix_subject_scope_class_stream"):
        op.create_index(
            "ix_subject_scope_class_stream",
            "subject_academic_scopes",
            ["class_level", "stream"],
            unique=False,
        )

    if not _has_index(inspector, "subject_academic_scopes", "ix_subject_scope_subject"):
        op.create_index(
            "ix_subject_scope_subject",
            "subject_academic_scopes",
            ["subject_id"],
            unique=False,
        )

    if inspector.has_table("subjects"):
        _seed_default_scopes(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("subject_academic_scopes") and _has_index(inspector, "subject_academic_scopes", "ix_subject_scope_subject"):
        op.drop_index("ix_subject_scope_subject", table_name="subject_academic_scopes")
    if inspector.has_table("subject_academic_scopes") and _has_index(inspector, "subject_academic_scopes", "ix_subject_scope_class_stream"):
        op.drop_index("ix_subject_scope_class_stream", table_name="subject_academic_scopes")

    inspector = sa.inspect(bind)
    if inspector.has_table("subject_academic_scopes"):
        op.drop_table("subject_academic_scopes")
