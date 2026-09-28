"""Reference comparison: the dedicated Warcraft Logs login, officers' queued requests, and the worker's results

Revision ID: 0009
Revises: 0008
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_login",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("connection_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("connected_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "reference_jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("raid_day", sa.String(32), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reference_jobs_created_at", "reference_jobs", ["created_at"])
    op.create_table(
        "reference_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("guild_raids", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reference_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_report", sa.String(32), nullable=False),
        sa.Column("reference_report", sa.String(32), nullable=False),
        sa.Column("guild_title", sa.String(200), nullable=False),
        sa.Column("reference_title", sa.String(200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("guild_report", "reference_report", name="uq_reference_comparisons_pair"),
    )
    op.create_index("ix_reference_comparisons_updated_at", "reference_comparisons", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_reference_comparisons_updated_at", "reference_comparisons")
    op.drop_table("reference_comparisons")
    op.drop_table("reference_pages")
    op.drop_index("ix_reference_jobs_created_at", "reference_jobs")
    op.drop_table("reference_jobs")
    op.drop_table("reference_login")
