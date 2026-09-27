"""community_ids: one id sequence shared by every community record

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
    op.create_table("community_ids", sa.Column("id", sa.Integer(), nullable=False), sa.PrimaryKeyConstraint("id"))


def downgrade() -> None:
    op.drop_table("community_ids")
