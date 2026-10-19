"""Absences members report for the raid nights they will miss

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_absences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raid_day", sa.String(32), nullable=False),
        sa.Column("first_date", sa.Date(), nullable=False),
        sa.Column("last_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_member_absences_member_id", "member_absences", ["member_id"])
    op.create_index("ix_member_absences_day_last", "member_absences", ["raid_day", "last_date"])


def downgrade() -> None:
    op.drop_index("ix_member_absences_day_last", table_name="member_absences")
    op.drop_index("ix_member_absences_member_id", table_name="member_absences")
    op.drop_table("member_absences")
