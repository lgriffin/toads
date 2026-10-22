"""Highlights wait for an officer: photos and streams gain approved_at, and gallery_trusted_channels remembers the
Twitch channels an officer approved for a member. Everything already on the page counts as approved.

Revision ID: 0038
Revises: 0037
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("gallery_photos") as batch:
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column(
                "approved_by",
                sa.Integer(),
                sa.ForeignKey("members.id", ondelete="SET NULL", name="fk_gallery_photos_approved_by_members"),
                nullable=True,
            )
        )
        batch.create_index("ix_gallery_photos_approved_at", ["approved_at"])
    with op.batch_alter_table("live_streams") as batch:
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "gallery_trusted_channels",
        sa.Column("discord_user_id", sa.BigInteger(), primary_key=True),
        sa.Column("channel", sa.String(25), primary_key=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
    )
    # What members already saw stays up; their channels stay trusted.
    op.execute("UPDATE gallery_photos SET approved_at = created_at")
    op.execute("UPDATE live_streams SET approved_at = started_at")
    op.execute(
        "INSERT INTO gallery_trusted_channels (discord_user_id, channel, approved_at) "
        "SELECT discord_user_id, channel, MIN(started_at) FROM live_streams GROUP BY discord_user_id, channel"
    )


def downgrade() -> None:
    op.drop_table("gallery_trusted_channels")
    with op.batch_alter_table("live_streams") as batch:
        batch.drop_column("approved_at")
    with op.batch_alter_table("gallery_photos") as batch:
        batch.drop_index("ix_gallery_photos_approved_at")
        batch.drop_column("approved_by")
        batch.drop_column("approved_at")
