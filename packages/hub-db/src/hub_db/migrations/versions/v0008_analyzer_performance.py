"""Each raider's numbers in the guild's last raid against the role median, for members' "Your performance" widget

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyzer_performance_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("raid", sa.JSON(), nullable=True),
        sa.Column("players", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analyzer_performance_pages")
