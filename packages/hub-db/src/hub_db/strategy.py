"""Raid strategy docs (docs/strategy.md): the Google Docs officers pin per raid, and which raid each night is running.

Which raids exist is the API's (`toads_api.strategy.service.RAIDS`); a row only names its raid by id.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class StrategyDoc(Base):
    """A strategy doc pinned to a raid. The newest one for a raid is its pinned doc; older ones are kept as the docs
    it replaced, so officers can see what came before."""

    __tablename__ = "strategy_docs"
    __table_args__ = (Index("ix_strategy_docs_raid", "raid", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    raid: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(80))
    url: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NightRaid(Base):
    """The raid a raid day is running, which picks the strategy doc its Raid page shows."""

    __tablename__ = "night_raids"

    # The raid day's id from config/raid_days.yaml (not a foreign key: raid days are config, not rows).
    raid_day_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    raid: Mapped[str] = mapped_column(String(16))
    set_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
