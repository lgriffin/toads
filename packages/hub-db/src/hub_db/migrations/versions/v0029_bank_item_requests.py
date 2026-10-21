"""The bank request desk: members' item requests and the officers' answers

Revision ID: 0029
Revises: 0028
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_item_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("requester_name", sa.String(100), nullable=False),
        sa.Column("item", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("officer_message", sa.String(500), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_by_name", sa.String(100), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notice_job_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_bank_item_requests_discord_user_id", "bank_item_requests", ["discord_user_id"])
    op.create_index("ix_bank_item_requests_status", "bank_item_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_bank_item_requests_status", table_name="bank_item_requests")
    op.drop_index("ix_bank_item_requests_discord_user_id", table_name="bank_item_requests")
    op.drop_table("bank_item_requests")
