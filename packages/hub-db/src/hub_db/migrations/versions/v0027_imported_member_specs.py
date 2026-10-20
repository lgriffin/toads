"""Members' specs: where a spec came from, when it was not the member's own choice (a Raid-Helper import)

Revision ID: 0027
Revises: 0026
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("member_specs") as batch:
        batch.add_column(sa.Column("imported_from", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("member_specs") as batch:
        batch.drop_column("imported_from")
