"""Bank grants: Discord users who may import bank snapshots or run the request queue without being officers

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("permission", sa.String(32), nullable=False),
        # "*" for every bank, so the unique constraint covers those grants too.
        sa.Column("raid_day", sa.String(32), nullable=False),
        sa.Column("granted_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("discord_user_id", "permission", "raid_day", name="uq_bank_grants_user_permission_day"),
    )


def downgrade() -> None:
    op.drop_table("bank_grants")
