"""Community tables: posts, applications and their events, recruitment needs, highlights, spotlights, bot outbox

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bot_outbox_done"), "bot_outbox", ["done"], unique=False)
    op.create_table(
        "recruitment_needs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(length=20), nullable=False),
        sa.Column("spec", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.Column("priority", sa.String(length=8), nullable=False),
        sa.Column("raid_days", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("character_name", sa.String(length=12), nullable=False),
        sa.Column("class_name", sa.String(length=20), nullable=False),
        sa.Column("spec", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.Column("raid_days", sa.JSON(), nullable=False),
        sa.Column("experience", sa.Text(), nullable=False),
        sa.Column("availability", sa.String(length=300), nullable=False),
        sa.Column("logs_url", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("interview_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_member_id"), "applications", ["member_id"], unique=False)
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_member_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=100), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("raid_day_id", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("publish_to_discord", sa.Boolean(), nullable=False),
        sa.Column("discord_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("discord_message_id", sa.BigInteger(), nullable=True),
        sa.Column("edited_since_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["author_member_id"],
            ["members.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discord_message_id", name="uq_post_discord_message"),
    )
    op.create_index(op.f("ix_community_posts_raid_day_id"), "community_posts", ["raid_day_id"], unique=False)
    op.create_index(op.f("ix_community_posts_status"), "community_posts", ["status"], unique=False)
    op.create_table(
        "highlights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("clip_id", sa.String(length=100), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("raid_id", sa.String(length=64), nullable=True),
        sa.Column("boss", sa.String(length=60), nullable=True),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["members.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_highlights_status"), "highlights", ["status"], unique=False)
    op.create_index(op.f("ix_highlights_submitted_by"), "highlights", ["submitted_by"], unique=False)
    op.create_table(
        "spotlights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("character_name", sa.String(length=12), nullable=False),
        sa.Column("class_name", sa.String(length=20), nullable=False),
        sa.Column("headline", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("written_by", sa.Integer(), nullable=False),
        sa.Column("consent", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
        ),
        sa.ForeignKeyConstraint(
            ["written_by"],
            ["members.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_spotlights_member_id"), "spotlights", ["member_id"], unique=False)
    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("actor_member_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_member_id"],
            ["members.id"],
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_events_application_id"), "application_events", ["application_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_application_events_application_id"), table_name="application_events")
    op.drop_table("application_events")
    op.drop_index(op.f("ix_spotlights_member_id"), table_name="spotlights")
    op.drop_table("spotlights")
    op.drop_index(op.f("ix_highlights_submitted_by"), table_name="highlights")
    op.drop_index(op.f("ix_highlights_status"), table_name="highlights")
    op.drop_table("highlights")
    op.drop_index(op.f("ix_community_posts_status"), table_name="community_posts")
    op.drop_index(op.f("ix_community_posts_raid_day_id"), table_name="community_posts")
    op.drop_table("community_posts")
    op.drop_index(op.f("ix_applications_status"), table_name="applications")
    op.drop_index(op.f("ix_applications_member_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_table("recruitment_needs")
    op.drop_index(op.f("ix_bot_outbox_done"), table_name="bot_outbox")
    op.drop_table("bot_outbox")
