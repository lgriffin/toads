"""Members' specs and raid days, and the comps officers lock in

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
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("raid_days", sa.JSON(), nullable=True))
    op.create_table(
        "member_specs",
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("wow_class", sa.String(16), nullable=False),
        sa.Column("primary_spec", sa.String(32), nullable=False),
        sa.Column("secondary_spec", sa.String(32), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "raid_comps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("raid_day_id", "name", name="uq_raid_comp_name"),
    )
    op.create_index("ix_raid_comps_raid_day_id", "raid_comps", ["raid_day_id"])


def downgrade() -> None:
    op.drop_index("ix_raid_comps_raid_day_id", table_name="raid_comps")
    op.drop_table("raid_comps")
    op.drop_table("member_specs")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("raid_days")
