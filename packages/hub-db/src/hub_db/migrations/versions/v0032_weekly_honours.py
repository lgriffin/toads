"""Awards: weekly honours (Raider of the Week, Sunder King, ...) store their ISO week, "YYYY-Www", in the period

Revision ID: 0032
Revises: 0031
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("member_awards") as batch:
        batch.alter_column(
            "period",
            existing_type=sa.String(7),
            type_=sa.String(8),
            existing_nullable=False,
            existing_server_default="",
        )


def downgrade() -> None:
    # Weekly honours ("YYYY-Www") do not fit, or exist, before this revision.
    op.execute(sa.text("DELETE FROM member_awards WHERE period LIKE '%-W%'"))
    with op.batch_alter_table("member_awards") as batch:
        batch.alter_column(
            "period",
            existing_type=sa.String(8),
            type_=sa.String(7),
            existing_nullable=False,
            existing_server_default="",
        )
