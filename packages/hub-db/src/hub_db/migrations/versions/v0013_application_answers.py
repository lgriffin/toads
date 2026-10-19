"""Applications ask for a secondary role and why Toads

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("applications") as batch:
        batch.add_column(sa.Column("secondary_role", sa.String(8), nullable=True))
        batch.add_column(sa.Column("why_toads", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("applications") as batch:
        batch.drop_column("why_toads")
        batch.drop_column("secondary_role")
