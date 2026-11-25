"""Officers: the sign-in audit, one row for each time a member signs in, with the raid nights they were on then

Revision ID: 0044
Revises: 0043
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sign_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raid_days", sa.JSON(), nullable=False),
    )
    op.create_index("ix_sign_ins_member_id", "sign_ins", ["member_id"])
    op.create_index("ix_sign_ins_at", "sign_ins", ["at"])


def downgrade() -> None:
    op.drop_index("ix_sign_ins_at", table_name="sign_ins")
    op.drop_index("ix_sign_ins_member_id", table_name="sign_ins")
    op.drop_table("sign_ins")
