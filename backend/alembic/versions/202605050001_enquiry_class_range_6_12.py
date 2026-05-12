"""expand enquiry class range to 6-12

Revision ID: 202605050001
Revises: 202605030001
Create Date: 2026-05-05 18:45:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202605050001"
down_revision = "202605030001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "student_enquiries" not in inspector.get_table_names():
        return

    existing_checks = {item.get("name") for item in inspector.get_check_constraints("student_enquiries")}

    with op.batch_alter_table("student_enquiries", recreate="always") as batch_op:
        if "ck_student_enquiry_class_level" in existing_checks:
            batch_op.drop_constraint("ck_student_enquiry_class_level", type_="check")
        if "ck_student_enquiry_fee_class_level" in existing_checks:
            batch_op.drop_constraint("ck_student_enquiry_fee_class_level", type_="check")

        batch_op.create_check_constraint(
            "ck_student_enquiry_class_level",
            "class_level IN (6, 7, 8, 9, 10, 11, 12)",
        )
        batch_op.create_check_constraint(
            "ck_student_enquiry_fee_class_level",
            "fee_class_level IN (6, 7, 8, 9, 10, 11, 12)",
        )


def downgrade() -> None:
    # Non-destructive downgrade by design.
    pass
