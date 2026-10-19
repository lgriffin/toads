"""Badges a super admin ties to Discord roles

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discord_role_badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_role_id", sa.BigInteger(), nullable=False),
        sa.Column("badge_id", sa.String(48), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("discord_role_id", "badge_id", name="uq_discord_role_badge"),
    )
    op.create_index("ix_discord_role_badges_discord_role_id", "discord_role_badges", ["discord_role_id"])


def downgrade() -> None:
    op.drop_index("ix_discord_role_badges_discord_role_id", table_name="discord_role_badges")
    op.drop_table("discord_role_badges")
