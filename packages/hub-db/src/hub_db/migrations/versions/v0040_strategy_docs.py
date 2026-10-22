"""Raid strategy docs: the Google Docs officers pin per raid, and the raid each night is running

Revision ID: 0040
Revises: 0039
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_docs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid", sa.String(16), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_strategy_docs_raid", "strategy_docs", ["raid", "id"])
    op.create_table(
        "night_raids",
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("raid", sa.String(16), nullable=False),
        sa.Column("set_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("night_raids")
    op.drop_index("ix_strategy_docs_raid", table_name="strategy_docs")
    op.drop_table("strategy_docs")
