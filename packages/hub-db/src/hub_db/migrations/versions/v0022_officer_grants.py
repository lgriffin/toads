"""Officer grants: officer powers a super admin gives one Discord member, for one raid day or every day

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "officer_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(32), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("raid_day", sa.String(32), nullable=False),
        sa.Column("granted_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("discord_user_id", "raid_day", name="uq_officer_grants_user_day"),
    )
    op.create_index("ix_officer_grants_discord_user_id", "officer_grants", ["discord_user_id"])


def downgrade() -> None:
    op.drop_index("ix_officer_grants_discord_user_id", table_name="officer_grants")
    op.drop_table("officer_grants")
