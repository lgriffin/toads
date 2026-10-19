"""Raid compositions (docs/comps.md): each member's primary and secondary spec, and the comps officers lock in for a
raid day.

Which classes and specs exist is the API's catalogue (`toads_api.comps.catalog`); rows here only name them by id, so
the catalogue can change without a migration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class MemberSpec(Base):
    """The class a member raids as and the specs they play: a primary, and optionally a secondary of the same class."""

    __tablename__ = "member_specs"

    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    wow_class: Mapped[str] = mapped_column(String(16))
    primary_spec: Mapped[str] = mapped_column(String(32))
    secondary_spec: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RaidComp(Base):
    """A composition an officer locked in for a raid day. `slots` holds one entry per raid seat, in group order:
    null for an empty seat, else {"spec": spec id, "member_id": member id or null}."""

    __tablename__ = "raid_comps"
    __table_args__ = (UniqueConstraint("raid_day_id", "name", name="uq_raid_comp_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    raid_day_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column()
    slots: Mapped[list[dict[str, object] | None]] = mapped_column(JSON)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
