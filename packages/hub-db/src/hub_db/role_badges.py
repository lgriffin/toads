"""Role badges: which Discord server role earns which badge toad, set by a super admin (docs/role-badges.md).

Which badges exist is the API's catalogue (`toads_api.role_badges.catalog`); a row here only names one by id, so
retiring a badge from the catalogue never needs a migration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class DiscordRoleBadge(Base):
    """One Discord role earning one badge. A role may earn several badges and a badge may come from several roles."""

    __tablename__ = "discord_role_badges"
    __table_args__ = (UniqueConstraint("discord_role_id", "badge_id", name="uq_discord_role_badge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_role_id: Mapped[int] = mapped_column(BigInteger, index=True)
    badge_id: Mapped[str] = mapped_column(String(48))
    # The role's name when the badge was tied to it, so the list still reads when Discord is not answering.
    role_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    added_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
