"""Officers: links a raid day's officers pin to their night (the strategy doc, the role sheet on Google Drive)

Revision ID: 0032
Revises: 0031
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "night_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_night_links_day", "night_links", ["raid_day_id", "position"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_night_links_day", table_name="night_links")
    op.drop_table("night_links")
