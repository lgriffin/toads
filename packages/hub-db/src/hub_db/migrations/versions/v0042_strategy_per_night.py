"""Strategy docs per night: a doc can be pinned for one raid night (raid_day_id) or every night (NULL), and a night
can run several raids (night_raid_choices replaces night_raids, one row per night and raid)

Revision ID: 0042
Revises: 0041
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.execute(
        "INSERT INTO night_raid_choices (raid_day_id, raid, position, set_by, set_at) "
        "SELECT raid_day_id, raid, 0, set_by, set_at FROM night_raids"
    )
    op.drop_table("night_raids")


def downgrade() -> None:
    op.create_table(
        "night_raids",
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("raid", sa.String(16), nullable=False),
        sa.Column("set_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
    )
    # A night keeps only its first raid.
    op.execute(
        "INSERT INTO night_raids (raid_day_id, raid, set_by, set_at) "
        "SELECT raid_day_id, raid, set_by, set_at FROM night_raid_choices WHERE position = 0"
    )
    op.drop_table("night_raid_choices")
    op.execute("DELETE FROM strategy_docs WHERE raid_day_id IS NOT NULL")
    with op.batch_alter_table("strategy_docs") as batch:
        batch.drop_column("raid_day_id")
