"""Logs: the analyzer's home widgets built per raid night, one row per raid day

Revision ID: 0026
Revises: 0025
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "night_home_pages",
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("widgets", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("night_home_pages")
