"""The officers' task board, one per raid day

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
        "officer_board_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), nullable=False),
        sa.Column("lane", sa.String(16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("assignee_member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_officer_board_cards_day_lane", "officer_board_cards", ["raid_day_id", "lane", "position"])


def downgrade() -> None:
    op.drop_index("ix_officer_board_cards_day_lane", table_name="officer_board_cards")
    op.drop_table("officer_board_cards")
