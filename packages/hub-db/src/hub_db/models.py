"""Hub tables. Analyzer tables (raids, characters, *_performance) are owned by wcl-store.

The H1/H2 tables are here, the community tables are in `community.py` and bank grants in `bank.py` (the bank's own
data lives in ToadsBank); screenshots, albums and signups arrive with their milestones. Every change here needs a
migration in `hub_db/migrations/versions/`; `test_migrations.py` fails when the two drift apart.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Member(Base):
    """A Discord user who has logged in to the hub. Roles are never stored here (REQ-HUB-RBAC-001)."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    # The member's server nickname, refreshed at every sign-in. The name the hub shows may differ: see name_source.
    display_name: Mapped[str] = mapped_column(String(100))
    # Which name the hub shows for this member: "discord" (display_name) or "character" (name_character_id's name,
    # honoured only while the member holds an approved claim on it).
    name_source: Mapped[str] = mapped_column(String(16), default="discord", server_default="discord")
    name_character_id: Mapped[int | None] = mapped_column()
    profile_public: Mapped[bool] = mapped_column(default=False)
    dms_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MemberHomeLayout(Base):
    """The widgets a member placed on their hub home, in order: [{"id": ..., "shown": ...}]. No row means the
    default layout. Which widgets exist is decided by the API's home service, not stored here."""

    __tablename__ = "member_home_layouts"

    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    widgets: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalyzerHomePage(Base):
    """The analyzer's home page (wcl_app.home) as the worker last built it: guild-wide, one row. The payload is the
    analyzer's JSON contract, stored as published."""

    __tablename__ = "analyzer_home_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column()
    generated_at: Mapped[str] = mapped_column(String(40))
    widgets: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalyzerPerformancePage(Base):
    """Each raider's primary number in the guild's last raid against the guild median for their role, as the worker
    last built it (toads_worker.jobs.performance): guild-wide, one row. The API shows each member only their own."""

    __tablename__ = "analyzer_performance_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column()
    generated_at: Mapped[str] = mapped_column(String(40))
    # {"report_id", "title", "date"}, or null before any raid is analysed.
    raid: Mapped[dict[str, object] | None] = mapped_column(JSON)
    players: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalyzerBadgePage(Base):
    """Every raider's Toads badges as the worker last built them (toads_worker.jobs.badges, wcl_app.badges):
    guild-wide, one row. The API shows each member only their own; officers see the last raid's roster on the hub
    home through the analyzer's `badges` widget."""

    __tablename__ = "analyzer_badge_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column()
    generated_at: Mapped[str] = mapped_column(String(40))
    # wcl_app PlayerBadges.to_dict() per player: {name, player_class, score, badges}.
    players: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ClaimStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CharacterClaim(Base):
    """Links a member to a wcl-store character. One character, one owner.

    Deleting a claim (unclaim, REQ-HUB-PRIV-003) detaches the member only; the character and its
    raid rows live in wcl-store and are never touched from here.
    """

    __tablename__ = "character_claims"
    __table_args__ = (UniqueConstraint("character_id", name="uq_claim_character"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    # FK to wcl-store's characters table is added by a later migration once wcl-store is published,
    # so hub-db does not import wcl-store.
    character_id: Mapped[int] = mapped_column(index=True)
    # Name as wcl-store knew it when the claim was made, so the officers' queue reads without a join.
    character_name: Mapped[str] = mapped_column(String(64))
    # The raid day whose officers decide this claim; NULL means only global officers can.
    raid_day_id: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, native_enum=False, values_callable=lambda e: [m.value for m in e], length=16),
        default=ClaimStatus.PENDING,
    )
    reason: Mapped[str | None] = mapped_column(String(200))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEntry(Base):
    """Every officer action, claim decision and refused cross-day attempt. Rows are never deleted."""

    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(200))
    raid_day_id: Mapped[str | None] = mapped_column(String(32), index=True)
    detail: Mapped[str | None] = mapped_column(String(500))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
