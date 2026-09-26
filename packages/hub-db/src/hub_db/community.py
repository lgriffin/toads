"""Community tables: posts mirrored both ways with Discord, applications, highlight reels, spotlights, bot outbox.

The API's CommunityRepository has the same shape; a Postgres repository over these tables replaces the in-memory one
with the phase 2.1 migrations.
Enum columns are stored as strings (native_enum=False) so values match the API schemas without a shared import.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class CommunityPost(Base):
    """An officer post written on the hub, or a Discord message an officer curated. One row per Discord message."""

    __tablename__ = "community_posts"
    __table_args__ = (UniqueConstraint("discord_message_id", name="uq_post_discord_message"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    author_member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    author_name: Mapped[str] = mapped_column(String(100))
    origin: Mapped[str] = mapped_column(String(16))  # hub | discord
    visibility: Mapped[str] = mapped_column(String(16))  # public | guild | raid_day
    raid_day_id: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending_review", index=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_to_discord: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    discord_message_id: Mapped[int | None] = mapped_column(BigInteger)
    edited_since_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Application(Base):
    """Someone asking to raid with the guild. Personal data kept to what officers need: no age, email or real name."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    character_name: Mapped[str] = mapped_column(String(12))
    class_name: Mapped[str] = mapped_column(String(20))
    spec: Mapped[str] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(8))
    raid_days: Mapped[list[str]] = mapped_column(JSON, default=list)  # empty: any day
    experience: Mapped[str] = mapped_column(Text)
    availability: Mapped[str] = mapped_column(String(300), default="")
    logs_url: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default="applied", index=True)
    interview_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApplicationEvent(Base):
    """Every status change on an application, with who made it. Never deleted."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    actor_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(String(500), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecruitmentNeed(Base):
    __tablename__ = "recruitment_needs"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_name: Mapped[str] = mapped_column(String(20))
    spec: Mapped[str] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(8))
    priority: Mapped[str] = mapped_column(String(8))
    raid_days: Mapped[list[str]] = mapped_column(JSON, default=list)


class Highlight(Base):
    """A clip on an allowlisted host. Only (provider, clip_id) is stored; embed URLs are rebuilt from them."""

    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(16))
    clip_id: Mapped[str] = mapped_column(String(100))
    submitted_by: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    raid_id: Mapped[str | None] = mapped_column(String(64))
    boss: Mapped[str | None] = mapped_column(String(60))
    visibility: Mapped[str] = mapped_column(String(16), default="guild")
    status: Mapped[str] = mapped_column(String(16), default="submitted", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Spotlight(Base):
    """An officer-written feature on a member. It is published only while its member's consent stands."""

    __tablename__ = "spotlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    character_name: Mapped[str] = mapped_column(String(12))
    class_name: Mapped[str] = mapped_column(String(20))
    headline: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    written_by: Mapped[int] = mapped_column(ForeignKey("members.id"))
    consent: Mapped[str] = mapped_column(String(16), default="pending")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BotOutbox(Base):
    """Work for the bot (open or lock an interview room, post or edit a message). The bot polls and acks."""

    __tablename__ = "bot_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
