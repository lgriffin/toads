"""The Logs page: stored raids with their analysis, and the boss history

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "log_raids",
        sa.Column("report_id", sa.String(32), primary_key=True),
        sa.Column("raid_date", sa.String(19), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("page", sa.JSON(), nullable=True),
        sa.Column("page_version", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_log_raids_raid_date", "log_raids", ["raid_date"])
    op.create_table(
        "log_index",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("bosses", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("log_index")
    op.drop_index("ix_log_raids_raid_date", table_name="log_raids")
    op.drop_table("log_raids")
