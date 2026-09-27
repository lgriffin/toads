"""Raid sheet snapshots: each downloaded tab of the guild's CBA and RPB spreadsheets, one row per content change.

The API's SheetRepository has the same shape. `kind` is stored as a string so values match the API schema
without a shared import.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base


class RaidSheetSnapshot(Base):
    __tablename__ = "raid_sheet_snapshots"
    __table_args__ = (
        Index("ix_raid_sheet_snapshots_raid", "raid_day_id", "raid_date"),
        # One row per version of a tab: concurrent imports of the same change cannot both add it.
        UniqueConstraint("spreadsheet_id", "tab", "version", name="uq_raid_sheet_snapshots_tab_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(8))  # cba | rpb
    spreadsheet_id: Mapped[str] = mapped_column(String(64))
    tab: Mapped[str] = mapped_column(String(100))
    raid_date: Mapped[date | None] = mapped_column(Date)
    raid_day_id: Mapped[str | None] = mapped_column(String(32))
    content_digest: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    headers: Mapped[list[str]] = mapped_column(JSON)
    rows: Mapped[list[list[str]]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column()
