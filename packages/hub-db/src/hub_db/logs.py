"""Logs: the analyzer's raid browser and raid analysis, as the worker last published them (docs/logs.md).

The worker builds them with wcl-app's RaidPageService (guides/raid_pages.md in lgriffin/warcraftlogs_project) and sends
the raid list with the boss history first, then each raid's analysis the hub does not hold yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now

# The one row of `log_index`.
INDEX_ROW = 1


class LogRaid(Base):
    """One stored guild raid: its line in the list and, once the worker has sent it, its analysis."""

    __tablename__ = "log_raids"

    report_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # "YYYY-MM-DD HH:MM:SS", the raid's local start; sorts as text.
    raid_date: Mapped[str] = mapped_column(String(19), index=True)
    # 0 for Monday to 6 for Sunday; None when the analyzer could not read the date.
    weekday: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    # RaidPage.to_dict(); None until the worker has sent it.
    page: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    page_version: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LogIndex(Base):
    """When the worker last sent the list, and the boss history it built from every stored raid."""

    __tablename__ = "log_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    generated_at: Mapped[str] = mapped_column(String(40))
    bosses: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
