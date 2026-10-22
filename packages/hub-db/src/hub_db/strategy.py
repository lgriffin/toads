"""Raid strategy docs (docs/strategy.md): the Google Docs officers add to each raid, and the ones each raid night pins
for its raiders.

Which raids exist is the API's (`toads_api.strategy.service.RAIDS`); a row only names its raid by id.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class StrategyDoc(Base):
    """A strategy doc added to a raid. A raid keeps every doc its officers add until one is taken down; a night shows
    its raiders only the docs it pins (NightDoc)."""

    __tablename__ = "strategy_docs"
    __table_args__ = (Index("ix_strategy_docs_raid", "raid", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    raid: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(80))
    url: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NightDoc(Base):
    """A doc a raid day pins for its raiders (a night may pin several, one per raid it runs or more), in order."""

    __tablename__ = "night_strategy_docs"

    # The raid day's id from config/raid_days.yaml (not a foreign key: raid days are config, not rows).
    raid_day_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("strategy_docs.id", ondelete="CASCADE"), primary_key=True)
    # The order the night's Raid page lists its docs in, from 0.
    position: Mapped[int] = mapped_column(default=0)
    set_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
