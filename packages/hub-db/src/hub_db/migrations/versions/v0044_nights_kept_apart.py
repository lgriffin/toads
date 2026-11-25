"""Raid nights are kept apart: strategy docs belong to the night they were added through (strategy_docs.raid_day_id),
and stored references and comparisons to the nights that imported or compared them (reference_nights), so one
night's officers no longer see or change another night's. What the global tier added stays shared (no night).

Each doc gets the night its `strategy.add` audit row names. A doc another night already pins stays shared, so no
night's Raid page loses a doc it shows; so does a doc with no audit row. References and comparisons get the nights of
the import and compare jobs still kept that succeeded; older ones stay shared.

Revision ID: 0044
Revises: 0043
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("strategy_docs") as batch:
        batch.add_column(sa.Column("raid_day_id", sa.String(32), nullable=True))
    op.execute(
        "UPDATE strategy_docs SET raid_day_id = ("
        " SELECT a.raid_day_id FROM audit a"
        " WHERE a.action = 'strategy.add' AND a.target = 'strategy_doc:' || CAST(strategy_docs.id AS VARCHAR)"
        " ORDER BY a.id DESC LIMIT 1)"
    )
    op.execute(
        "UPDATE strategy_docs SET raid_day_id = NULL WHERE raid_day_id IS NOT NULL AND EXISTS ("
        " SELECT 1 FROM night_strategy_docs n"
        " WHERE n.doc_id = strategy_docs.id AND n.raid_day_id <> strategy_docs.raid_day_id)"
    )
    op.create_table(
        "reference_nights",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("raid_day_id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    jobs = sa.table(
        "reference_jobs",
        sa.column("kind", sa.String),
        sa.column("status", sa.String),
        sa.column("status", sa.String),
        sa.column("raid_day", sa.String),
        sa.column("params", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    bind = op.get_bind()
    owners: dict[tuple[str, str], object] = {}
    done = sa.select(jobs.c.kind, jobs.c.raid_day, jobs.c.params, jobs.c.created_at).where(jobs.c.status == "done")
    for kind, day, params, at in bind.execute(done):
        key = _key(kind, params or {})
        if key and day:
            owners.setdefault((key[:80], day), at)
    if owners:
        nights = sa.table(
            "reference_nights",
            sa.column("key", sa.String),
            sa.column("raid_day_id", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(nights, [{"key": k, "raid_day_id": d, "created_at": at} for (k, d), at in owners.items()])


def _key(kind: str, params: dict[str, object]) -> str | None:
    if kind == "import" and params.get("report"):
        return str(params["report"])
    if kind == "compare" and params.get("guild_report") and params.get("reference_report"):
        return f"{params['guild_report']}/{params['reference_report']}"
    return None


def downgrade() -> None:
    op.drop_table("reference_nights")
    with op.batch_alter_table("strategy_docs") as batch:
        batch.drop_column("raid_day_id")
