"""Professions (docs/professions.md): the professions each member says they have, and the members officers name as
the guild's crafters for a profession, the people the guild sends its top end recipes to.

Which professions and specialisations exist is the API's catalogue (`toads_api.professions.catalog`); rows here only
name them by id, so the catalogue can change without a migration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class MemberProfession(Base):
    """One profession a member has, with the skill and specialisation they gave, if any."""

    __tablename__ = "member_professions"

    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    profession: Mapped[str] = mapped_column(String(24), primary_key=True)
    skill: Mapped[int | None] = mapped_column(Integer)
    specialisation: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GuildCrafter(Base):
    """A member an officer named as one of the guild's crafters for a profession. A member is only ever named for a
    profession they list, and the row goes when they stop listing it."""

    __tablename__ = "guild_crafters"

    profession: Mapped[str] = mapped_column(String(24), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    # What the guild sends them, in the officer's words ("Flasks and transmutes").
    note: Mapped[str | None] = mapped_column(String(200))
    designated_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    designated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
