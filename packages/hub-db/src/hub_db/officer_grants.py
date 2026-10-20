"""Officer grants: officer powers a super admin gives one Discord member on top of their Discord roles (docs/admin.md
"Officer grants").

Officers normally come from Discord roles in raid_days.yaml. A grant makes one more member an officer of one raid day,
or a global officer (EVERY_DAY). Nothing here can make anyone a super admin: those are named in configuration alone.
Grants are read per request, so a revoke takes effect on the member's next call.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class OfficerGrant(Base):
    __tablename__ = "officer_grants"
    __table_args__ = (UniqueConstraint("discord_user_id", "raid_day", name="uq_officer_grants_user_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The grantee's Discord user id: they need not have signed in to the hub yet.
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Their Discord username and server name when they were granted, for listing; nothing is decided by them.
    username: Mapped[str] = mapped_column(String(32), default="", server_default="")
    display_name: Mapped[str] = mapped_column(String(100))
    # The raid day they are an officer of; hub_db.EVERY_DAY makes them a global officer.
    raid_day: Mapped[str] = mapped_column(String(32))
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
