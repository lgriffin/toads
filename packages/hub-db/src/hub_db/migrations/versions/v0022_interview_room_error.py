"""Recruitment: why the Toad Bot could not open an applicant's interview room

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("interview_room_error", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "interview_room_error")
