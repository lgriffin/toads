"""Hub tables. Analyzer tables (raids, characters, *_performance) are owned by wcl-store.

Only the H1/H2 tables are here; screenshots, albums, signups, discord_messages and the
bank_* tables arrive with their milestones. Every change here needs a migration in
`hub_db/migrations/versions/`; `test_migrations.py` fails when the two drift apart.
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
    """A Discord user who has logged in to the hub. Roles are never stored here (REQ-HUB-RBAC-001)."""

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
