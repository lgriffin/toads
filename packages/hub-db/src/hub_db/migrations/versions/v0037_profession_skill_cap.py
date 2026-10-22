"""Professions cap at 300 on Classic Forever: bring any skill saved above it down to 300

Revision ID: 0037
Revises: 0036
"""

from __future__ import annotations

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE member_professions SET skill = 300 WHERE skill > 300")


def downgrade() -> None:
    # The skills that were above 300 are not kept, and 300 is a valid skill under the old cap too.
    pass
