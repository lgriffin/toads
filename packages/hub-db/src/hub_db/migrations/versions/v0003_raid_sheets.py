"""Raid sheet snapshots: the guild's CBA and RPB spreadsheet tabs, linked to raids by date and raid day

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raid_sheet_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("spreadsheet_id", sa.String(length=64), nullable=False),
        sa.Column("tab", sa.String(length=100), nullable=False),
        sa.Column("raid_date", sa.Date(), nullable=True),
        sa.Column("raid_day_id", sa.String(length=32), nullable=True),
        sa.Column("content_digest", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raid_sheet_snapshots_raid", "raid_sheet_snapshots", ["raid_day_id", "raid_date"], unique=False)
    op.create_index("ix_raid_sheet_snapshots_tab", "raid_sheet_snapshots", ["spreadsheet_id", "tab"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raid_sheet_snapshots_tab", table_name="raid_sheet_snapshots")
    op.drop_index("ix_raid_sheet_snapshots_raid", table_name="raid_sheet_snapshots")
    op.drop_table("raid_sheet_snapshots")
