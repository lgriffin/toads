"""Recruitment: each raid night's interview panel, picked by its officers from the Discord server

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_panelists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("raid_day_id", "discord_user_id", name="uq_interview_panelist"),
    )
    op.create_index("ix_interview_panelists_raid_day_id", "interview_panelists", ["raid_day_id"])


def downgrade() -> None:
    op.drop_index("ix_interview_panelists_raid_day_id", table_name="interview_panelists")
    op.drop_table("interview_panelists")
