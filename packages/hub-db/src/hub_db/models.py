"""Hub tables. Analyzer tables (raids, characters, *_performance) are owned by wcl-store.

The H1/H2 tables are here and the community tables are in `community.py`; screenshots, albums, signups and the
bank_* tables arrive with their milestones.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Member(Base):
    """A Discord user who has logged in to the hub. Roles are never stored here as truth."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    profile_public: Mapped[bool] = mapped_column(default=False)
    dms_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ClaimStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CharacterClaim(Base):
    """Links a member to a wcl-store character. One character, one owner."""

    __tablename__ = "character_claims"
    __table_args__ = (UniqueConstraint("character_id", name="uq_claim_character"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    # FK to wcl-store's characters table is added in the Alembic migration, not here,
    # so hub-db does not import wcl-store.
    character_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, native_enum=False), default=ClaimStatus.PENDING)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEntry(Base):
    """Every officer action and claim decision. Rows are never deleted."""

    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(200))
    raid_day_id: Mapped[str | None] = mapped_column(String(32), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
