"""Officers' loot priority: per raid day, the big-ticket items its officers track and who gets each one first
(docs/loot.md).

An item is named by its game id and the canonical name it had when an officer added it; the item catalogue itself is
the API's (`toads_api.loot.catalogue`), not a table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class LootItem(Base):
    """One item on a raid day's loot list, with the officers' note on it."""

    __tablename__ = "loot_items"
    # One list per item per night, so two officers adding it at once cannot split its priority in two.
    __table_args__ = (Index("ix_loot_items_day_item", "raid_day_id", "item_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The raid day's id from config/raid_days.yaml (not a foreign key: raid days are config, not rows).
    raid_day_id: Mapped[str] = mapped_column(String(32))
    # The game's item id: the same number Wowhead's item pages use.
    item_id: Mapped[int] = mapped_column(Integer)
    item_name: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LootRecipient(Base):
    """A member in line for an item: rank 1 gets the first drop, rank 2 the next. `received_at` is set once they have
    it."""

    __tablename__ = "loot_recipients"
    __table_args__ = (Index("ix_loot_recipients_item_member", "loot_item_id", "member_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    loot_item_id: Mapped[int] = mapped_column(ForeignKey("loot_items.id", ondelete="CASCADE"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    # From 1; the service keeps an item's ranks contiguous.
    rank: Mapped[int] = mapped_column(Integer)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
