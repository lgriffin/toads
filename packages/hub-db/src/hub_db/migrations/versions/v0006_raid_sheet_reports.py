"""Raid sheet snapshots record the Warcraft Logs report they were run for; setup tabs are no longer kept

The CBA and RPB templates keep the runner's Discord webhook, e-mail and API key on their setup tabs, which the
importer now drops. Any copies an earlier import stored are deleted here.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("raid_sheet_snapshots") as batch:
        batch.add_column(sa.Column("report_code", sa.String(length=32), nullable=True))
    snapshots = sa.table("raid_sheet_snapshots", sa.column("tab", sa.String))
    tab = sa.func.lower(snapshots.c.tab)
    op.execute(
        snapshots.delete().where(
            sa.or_(tab.in_(["instructions", "trans", "settings", "all", "start"]), tab.like("%config%"))
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("raid_sheet_snapshots") as batch:
        batch.drop_column("report_code")
