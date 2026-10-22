"""Highlights: members' photos from the Toad Bot, the photo of the week, and live Twitch streams

Revision ID: 0035
Revises: 0034
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gallery_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("uploader_name", sa.String(100), nullable=False),
        sa.Column("caption", sa.String(200), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gallery_photos_discord_user_id", "gallery_photos", ["discord_user_id"])
    op.create_index("ix_gallery_photos_created_at", "gallery_photos", ["created_at"])
    op.create_table(
        "gallery_photo_files",
        sa.Column("photo_id", sa.Integer(), sa.ForeignKey("gallery_photos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("thumbnail", sa.LargeBinary(), nullable=False),
    )
    op.create_table(
        "photo_of_the_week",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("photo_id", sa.Integer(), sa.ForeignKey("gallery_photos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chosen_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chosen_by_name", sa.String(100), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_photo_of_the_week_photo_id", "photo_of_the_week", ["photo_id"])
    op.create_index("ix_photo_of_the_week_ends_at", "photo_of_the_week", ["ends_at"])
    op.create_table(
        "live_streams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("streamer_name", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(25), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_live_streams_discord_user_id", "live_streams", ["discord_user_id"])
    op.create_index("ix_live_streams_ended_at", "live_streams", ["ended_at"])


def downgrade() -> None:
    op.drop_index("ix_live_streams_ended_at", table_name="live_streams")
    op.drop_index("ix_live_streams_discord_user_id", table_name="live_streams")
    op.drop_table("live_streams")
    op.drop_index("ix_photo_of_the_week_ends_at", table_name="photo_of_the_week")
    op.drop_index("ix_photo_of_the_week_photo_id", table_name="photo_of_the_week")
    op.drop_table("photo_of_the_week")
    op.drop_table("gallery_photo_files")
    op.drop_index("ix_gallery_photos_created_at", table_name="gallery_photos")
    op.drop_index("ix_gallery_photos_discord_user_id", table_name="gallery_photos")
    op.drop_table("gallery_photos")
