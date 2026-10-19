"""Absences: the raid nights a member has said they will miss (docs/absences.md).

A row covers a run of dates on one raid day's team; which nights that means comes from the raid day's weekday, so a
holiday is one row however many raids it spans.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class MemberAbsence(Base):
    """One member away from one raid day's team from `first_date` to `last_date`, both included."""

    __tablename__ = "member_absences"
    __table_args__ = (Index("ix_member_absences_day_last", "raid_day", "last_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    raid_day: Mapped[str] = mapped_column(String(32))
    first_date: Mapped[date] = mapped_column(Date)
    last_date: Mapped[date] = mapped_column(Date)
    # Why, in the member's words; only that raid day's officers see it.
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
