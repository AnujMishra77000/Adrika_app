"""force fee_structure class check to 6-12 (sqlite-safe)

Revision ID: 202605090003
Revises: 202605090002
Create Date: 2026-05-09 20:40:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "202605090003"
down_revision = "202605090002"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _ensure_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _rebuild_sqlite_fee_structures() -> None:
    op.execute("PRAGMA foreign_keys=OFF")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fee_structures__new (
            name VARCHAR(120) NOT NULL,
            class_level INTEGER NOT NULL,
            stream VARCHAR(20),
            total_amount NUMERIC(10, 2) NOT NULL,
            installment_count INTEGER NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL,
            id VARCHAR(36) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_fee_structure_class_level CHECK (class_level IN (6, 7, 8, 9, 10, 11, 12)),
            CONSTRAINT ck_fee_structure_stream CHECK (stream IS NULL OR stream IN ('science', 'commerce'))
        )
        """
    )
    op.execute(
        """
        INSERT INTO fee_structures__new (
            name, class_level, stream, total_amount, installment_count, description, is_active, id, created_at, updated_at
        )
        SELECT
            name, class_level, stream, total_amount, installment_count, description, is_active, id, created_at, updated_at
        FROM fee_structures
        """
    )
    op.execute("DROP TABLE fee_structures")
    op.execute("ALTER TABLE fee_structures__new RENAME TO fee_structures")
    op.execute("PRAGMA foreign_keys=ON")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "fee_structures"):
        return

    if bind.dialect.name == "sqlite":
        _rebuild_sqlite_fee_structures()
    else:
        with op.batch_alter_table("fee_structures") as batch_op:
            batch_op.drop_constraint("ck_fee_structure_class_level", type_="check")
            batch_op.create_check_constraint(
                "ck_fee_structure_class_level",
                "class_level IN (6, 7, 8, 9, 10, 11, 12)",
            )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "fee_structures") and not _ensure_index(
        inspector, "fee_structures", "ix_fee_structure_class_stream_active"
    ):
        op.create_index(
            "ix_fee_structure_class_stream_active",
            "fee_structures",
            ["class_level", "stream", "is_active"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "fee_structures"):
        return

    if bind.dialect.name == "sqlite":
        op.execute("PRAGMA foreign_keys=OFF")
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS fee_structures__old (
                name VARCHAR(120) NOT NULL,
                class_level INTEGER NOT NULL,
                stream VARCHAR(20),
                total_amount NUMERIC(10, 2) NOT NULL,
                installment_count INTEGER NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL,
                id VARCHAR(36) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_fee_structure_class_level CHECK (class_level IN (10, 11, 12)),
                CONSTRAINT ck_fee_structure_stream CHECK (stream IS NULL OR stream IN ('science', 'commerce'))
            )
            """
        )
        op.execute(
            """
            INSERT INTO fee_structures__old (
                name, class_level, stream, total_amount, installment_count, description, is_active, id, created_at, updated_at
            )
            SELECT
                name, class_level, stream, total_amount, installment_count, description, is_active, id, created_at, updated_at
            FROM fee_structures
            WHERE class_level IN (10, 11, 12)
            """
        )
        op.execute("DROP TABLE fee_structures")
        op.execute("ALTER TABLE fee_structures__old RENAME TO fee_structures")
        op.execute("PRAGMA foreign_keys=ON")
    else:
        with op.batch_alter_table("fee_structures") as batch_op:
            batch_op.drop_constraint("ck_fee_structure_class_level", type_="check")
            batch_op.create_check_constraint(
                "ck_fee_structure_class_level",
                "class_level IN (10, 11, 12)",
            )
