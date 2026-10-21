"""The officers' task board: one Trello-style board per raid day, seen and worked by that day's officers alone
(docs/officer-board.md).

Which lanes exist is the API's (`toads_api.officer_board.service.LANES`); a row only names its lane by id.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class OfficerBoardCard(Base):
    """One task on a raid day's board: what needs doing, who has it, when it is due, and which lane it sits in."""

    __tablename__ = "officer_board_cards"
    __table_args__ = (Index("ix_officer_board_cards_day_lane", "raid_day_id", "lane", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The raid day's id from config/raid_days.yaml (not a foreign key: raid days are config, not rows).
    raid_day_id: Mapped[str] = mapped_column(String(32))
    lane: Mapped[str] = mapped_column(String(16))
    # Order within the lane, from 0; the service keeps each lane's positions contiguous.
    position: Mapped[int] = mapped_column(default=0)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    assignee_member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    due_on: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NightLink(Base):
    """A link a raid day's officers pin to their night: the strategy doc, the role sheet, the Drive folder."""

    __tablename__ = "night_links"
    # Unique, so two officers pinning at once can never share a place (or slip past the night's limit together).
    __table_args__ = (Index("ix_night_links_day", "raid_day_id", "position", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    raid_day_id: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(default=0)
    label: Mapped[str] = mapped_column(String(80))
    url: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
