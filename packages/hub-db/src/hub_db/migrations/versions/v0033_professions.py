"""Professions: what each member has, and who the officers name as the guild's crafters

Revision ID: 0033
Revises: 0032
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_professions",
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("profession", sa.String(24), primary_key=True),
        sa.Column("skill", sa.Integer(), nullable=True),
        sa.Column("specialisation", sa.String(32), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "guild_crafters",
        sa.Column("profession", sa.String(24), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("designated_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("guild_crafters")
    op.drop_table("member_professions")
