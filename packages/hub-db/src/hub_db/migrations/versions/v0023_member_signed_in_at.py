"""Comp rosters from Discord: when each member last signed in, so raid-role holders listed from the server without
signing in can be told apart

Revision ID: 0023
Revises: 0022
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("members", sa.Column("signed_in_at", sa.DateTime(timezone=True), nullable=True))
    # Every row so far came from a sign-in (or a bot acting for a member, which the hub treated the same way).
    op.execute(sa.text("UPDATE members SET signed_in_at = created_at"))


def downgrade() -> None:
    op.drop_column("members", "signed_in_at")
