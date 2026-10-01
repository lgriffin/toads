"""Who may run the guild bank's upkeep besides officers (docs/bank.md "Grants", docs/admin.md).

ToadsBank owns the bank's data; the hub owns who may reach its officer routes. Officers hold every bank permission on
their raid day (global officers on every day) through their Discord roles. A grant lets one more Discord user hold one
bank permission, on one raid day's banks or on every bank. Super admins grant directly or mint an officer token whose
redeemer receives the grants it names. Grants are read per request, so a revoke takes effect on the member's next call.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base

# Stored in raid_day for a grant that covers every bank (raid day ids never contain it), so the unique constraint
# below holds for those too: SQL treats NULLs as distinct.
EVERY_DAY = "*"


def _now() -> datetime:
    return datetime.now(UTC)


class BankGrant(Base):
    __tablename__ = "bank_grants"
    __table_args__ = (
        UniqueConstraint("discord_user_id", "permission", "raid_day", name="uq_bank_grants_user_permission_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The grantee's Discord user id: they need not have signed in to the hub yet.
    discord_user_id: Mapped[int] = mapped_column(BigInteger)
    # Their server name when they were granted, for listing; the hub never decides anything by it.
    display_name: Mapped[str] = mapped_column(String(100))
    # A hub permission value: "import_bank_snapshot" or "manage_bank".
    permission: Mapped[str] = mapped_column(String(32))
    # The raid day whose banks it covers; EVERY_DAY covers every bank.
    raid_day: Mapped[str] = mapped_column(String(32))
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BankGrantToken(Base):
    """An officer token a super admin minted: whoever redeems it receives the grants it names. Only a hash of the token
    is kept; the token itself is shown once, when it is minted."""

    __tablename__ = "bank_grant_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    # SHA-256 of the token, hex.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # The hub permission values it grants.
    permissions: Mapped[list[str]] = mapped_column(JSON)
    # The raid day its grants cover; EVERY_DAY covers every bank.
    raid_day: Mapped[str] = mapped_column(String(32))
    # A note for the list ("for Bob's bank alt"); never the token.
    note: Mapped[str] = mapped_column(String(100), default="")
    minted_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    minted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    # The last redeemer (every redemption is on the audit log).
    used_by: Mapped[int | None] = mapped_column(BigInteger)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
