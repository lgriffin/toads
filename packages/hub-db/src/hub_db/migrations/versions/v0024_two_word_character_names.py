"""Recruitment: WoW Forever character names can be two words, so applications and spotlights hold up to 24 characters

Revision ID: 0024
Revises: 0023
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

TABLES = ("applications", "spotlights")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "character_name", type_=sa.String(24), existing_type=sa.String(12), existing_nullable=False
            )


def downgrade() -> None:
    # Names longer than 12 characters are cut to fit; the column cannot hold them any more.
    for table in TABLES:
        op.execute(sa.text(f"UPDATE {table} SET character_name = substr(character_name, 1, 12)"))  # noqa: S608 - fixed names
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "character_name", type_=sa.String(12), existing_type=sa.String(24), existing_nullable=False
            )
