"""Strategy docs are added to a raid, then a raid night pins the ones its raiders see: night_strategy_docs (one row
per night and doc, in order) replaces night_raid_choices, and a doc no longer belongs to one night

Each night keeps showing what it showed: for each raid it was running, the doc it would have shown (its own doc for the
raid, else the every-night one) is pinned for it.

Revision ID: 0043
Revises: 0042
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "night_strategy_docs",
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("strategy_docs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("set_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
    )
    # The doc a night running a raid showed before this revision: its own, else the raid's every-night one.
    op.execute(
        "INSERT INTO night_strategy_docs (raid_day_id, doc_id, position, set_by, set_at) "
        "SELECT raid_day_id, doc_id, position, set_by, set_at FROM ("
        " SELECT c.raid_day_id, c.position, c.set_by, c.set_at, COALESCE("
        "  (SELECT MAX(d.id) FROM strategy_docs d WHERE d.raid = c.raid AND d.raid_day_id = c.raid_day_id),"
        "  (SELECT MAX(d.id) FROM strategy_docs d WHERE d.raid = c.raid AND d.raid_day_id IS NULL)) AS doc_id"
        " FROM night_raid_choices c"
        ") shown WHERE doc_id IS NOT NULL"
    )
    op.drop_table("night_raid_choices")
    with op.batch_alter_table("strategy_docs") as batch:
        batch.drop_column("raid_day_id")


def downgrade() -> None:
    with op.batch_alter_table("strategy_docs") as batch:
        batch.add_column(sa.Column("raid_day_id", sa.String(32), nullable=True))
    op.create_table(
        "night_raid_choices",
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("raid", sa.String(16), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("set_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
    )
    # A night runs each raid it pinned a doc for, in the order of its first doc for that raid; every doc is kept for
    # every night.
    op.execute(
        "INSERT INTO night_raid_choices (raid_day_id, raid, position, set_by, set_at) "
        "SELECT n.raid_day_id, d.raid, MIN(n.position), MAX(n.set_by), MAX(n.set_at) "
        "FROM night_strategy_docs n JOIN strategy_docs d ON d.id = n.doc_id GROUP BY n.raid_day_id, d.raid"
    )
    op.drop_table("night_strategy_docs")
