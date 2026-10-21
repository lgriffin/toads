"""The first sign-in setup: when a member finished it, and characters they named that the logs have not seen yet

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
    # Left empty for everyone: each trial and raider meets the setup once at their next sign-in.
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("setup_done_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "declared_characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("wow_class", sa.String(16), nullable=False),
        sa.Column("main", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_declared_characters_member_id", "declared_characters", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_declared_characters_member_id", table_name="declared_characters")
    op.drop_table("declared_characters")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("setup_done_at")
