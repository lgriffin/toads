"""The Logs rules (docs/logs.md): who sees which raid's analysis, and what the worker may store.

Everyone signed in sees the raid list, each raid's boss kills and totals, and the boss history's kill counts and times.
Per-player numbers are per-raid detail (REQ-HUB-PRIV-001), so only officers see them: a global officer for every raid,
a raid day's officer for the raids held on that day's weekday.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from toads_api.logs.repository import LogRepository, RaidLine

# wcl-app's RAID_PAGE_VERSION this hub reads (guides/raid_pages.md in lgriffin/warcraftlogs_project).
PAGE_VERSION = 1
# wcl-app's RaidPageService.index default: every stored guild raid.
MAX_RAIDS = 1000
MAX_BOSSES = 200
# The most analyses the worker is asked for after one list, so a first run fills in over a few turns.
MAX_MISSING = 100
COMPOSITION_ROLES = ("tanks", "healers", "melee", "ranged")


class LogError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Viewer:
    """What the caller may open, worked out by the routes from their roles."""

    # A global officer: every raid in full.
    everything: bool = False
    # Raid days the caller is an officer on: that day's weekday in full.
    officer_days: tuple[str, ...] = ()


@dataclass(frozen=True)
class RaidRow:
    summary: dict[str, Any]
    analysed: bool
    # The raid day to open the full analysis under, for a raid day's officer; None reads it guild-wide.
    day: str | None
    full: bool


@dataclass(frozen=True)
class Overview:
    generated_at: str | None
    raids: list[RaidRow]
    bosses: list[dict[str, Any]]
    # The weekdays whose per-player numbers the caller sees; None for every weekday.
    full_weekdays: list[int] | None


@dataclass(frozen=True)
class RaidView:
    full: bool
    page: dict[str, Any]


def overview_of(page: dict[str, Any]) -> dict[str, Any]:
    """A raid's analysis without anyone's own numbers: the raid's size by role and each boss's totals."""
    composition = page.get("composition") or {}
    return {
        "summary": page.get("summary"),
        "duration_ms": page.get("duration_ms"),
        "version": page.get("version"),
        "composition_counts": {role: len(composition.get(role) or []) for role in COMPOSITION_ROLES},
        "encounters": [{k: v for k, v in e.items() if k != "players"} for e in page.get("encounters") or []],
    }


def _boss_days(boss: dict[str, Any], full: set[int] | None) -> dict[str, Any]:
    days: dict[str, Any] = {}
    for weekday, totals in (boss.get("days") or {}).items():
        shown = full is None or (weekday.isdigit() and int(weekday) in full)
        days[weekday] = totals if shown else {k: v for k, v in totals.items() if k != "players"}
    return {**boss, "days": days}


class LogService:
    def __init__(self, repo: LogRepository, weekdays: Mapping[str, int]) -> None:
        self._repo = repo
        # Each raid day's weekday (0 is Monday). A day without one opens no raid in full for its officers.
        self._weekdays = dict(weekdays)

    def _full_weekdays(self, viewer: Viewer) -> set[int] | None:
        if viewer.everything:
            return None
        return {self._weekdays[d] for d in viewer.officer_days if d in self._weekdays}

    def _day_for(self, viewer: Viewer, weekday: int | None) -> str | None:
        if viewer.everything or weekday is None:
            return None
        return next((d for d in viewer.officer_days if self._weekdays.get(d) == weekday), None)

    def overview(self, viewer: Viewer) -> Overview:
        index = self._repo.index()
        full = self._full_weekdays(viewer)
        rows = []
        for line in self._repo.raids():
            day = self._day_for(viewer, line.weekday)
            rows.append(
                RaidRow(line.summary, line.page_version == PAGE_VERSION, day, viewer.everything or day is not None)
            )
        return Overview(
            generated_at=index.generated_at if index else None,
            raids=rows,
            bosses=[_boss_days(b, full) for b in index.bosses] if index else [],
            full_weekdays=None if full is None else sorted(full),
        )

    def raid(self, report_id: str, viewer: Viewer, day: str | None = None) -> RaidView:
        """A raid's analysis: in full for an officer of its weekday (read under `day`) or a global officer, else its
        overview. 404 when the raid or its analysis is not here yet."""
        stored = self._repo.raid(report_id)
        if stored is None or stored.page is None or stored.line.page_version != PAGE_VERSION:
            raise LogError("This raid has not been analysed yet", 404)
        full = viewer.everything or (
            day is not None and day in viewer.officer_days and self._weekdays.get(day) == stored.line.weekday
        )
        return RaidView(full, stored.page if full else overview_of(stored.page))

    def publish_index(
        self, version: int, generated_at: str, raids: Sequence[dict[str, Any]], bosses: list[dict[str, Any]]
    ) -> list[str]:
        """Store the worker's list and boss history. Returns the raids whose analysis the hub still needs, newest
        first."""
        if version != PAGE_VERSION:
            raise LogError(f"This hub reads raid pages version {PAGE_VERSION}, not {version}", 422)
        lines = [RaidLine(str(r["report_id"]), str(r.get("raid_date") or ""), r.get("weekday"), dict(r)) for r in raids]
        if len({line.report_id for line in lines}) != len(lines):
            raise LogError("A raid is listed twice", 422)
        held = self._repo.index()
        if held is not None and generated_at < held.generated_at:
            # Two workers overlapping: the older build never replaces the newer one.
            raise LogError("A newer list is already stored", 409)
        self._repo.replace_index(generated_at, bosses, lines)
        missing = [line.report_id for line in self._repo.raids() if line.page_version != PAGE_VERSION]
        return missing[:MAX_MISSING]

    def publish_page(self, report_id: str, page: dict[str, Any]) -> None:
        version = page.get("version")
        if version != PAGE_VERSION:
            raise LogError(f"This hub reads raid pages version {PAGE_VERSION}, not {version}", 422)
        if (page.get("summary") or {}).get("report_id") != report_id:
            raise LogError("The page is for another raid", 422)
        if not self._repo.save_page(report_id, PAGE_VERSION, page):
            raise LogError("This raid is not in the list; send the list first", 404)
