"""Logs: the worker's hash of each raid's stored analysis and of the one its latest list built

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("log_raids", sa.Column("page_hash", sa.String(64), nullable=True))
    op.add_column("log_raids", sa.Column("want_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("log_raids", "want_hash")
    op.drop_column("log_raids", "page_hash")
