"""Officers: each raid day's loot list, the big-ticket items it tracks and the ranked members in line for each

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
        "loot_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_loot_items_day_item", "loot_items", ["raid_day_id", "item_id"], unique=True)
    op.create_table(
        "loot_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loot_item_id", sa.Integer(), sa.ForeignKey("loot_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_loot_recipients_item_member", "loot_recipients", ["loot_item_id", "member_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_loot_recipients_item_member", table_name="loot_recipients")
    op.drop_table("loot_recipients")
    op.drop_index("ix_loot_items_day_item", table_name="loot_items")
    op.drop_table("loot_items")
