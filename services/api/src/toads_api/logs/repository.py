"""Where the Logs pages live. LogService only talks to the LogRepository protocol; the hub-db backed implementation is
`sql.SqlLogRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class RaidLine:
    """One raid in the list, as the worker last sent it."""

    report_id: str
    raid_date: str
    # 0 for Monday to 6 for Sunday; None when the analyzer could not read the date.
    weekday: int | None
    # wcl-app's RaidSummary.to_dict().
    summary: dict[str, Any]
    # The version of the analysis the hub holds; None until the worker has sent it.
    page_version: int | None = None


@dataclass(frozen=True)
class StoredIndex:
    generated_at: str
    bosses: list[dict[str, Any]]


@dataclass(frozen=True)
class StoredRaid:
    line: RaidLine
    page: dict[str, Any] | None


class LogRepository(Protocol):
    def index(self) -> StoredIndex | None: ...
    def raids(self) -> list[RaidLine]: ...
    def raid(self, report_id: str) -> StoredRaid | None: ...
    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> None:
        """Keep exactly these raids (with any analysis already held for them) and this boss history."""
        ...

    def save_page(self, report_id: str, version: int, page: dict[str, Any]) -> bool:
        """Store a raid's analysis; False when the raid is not in the list."""
        ...


@dataclass
class InMemoryLogRepository:
    """For service tests."""

    stored_index: StoredIndex | None = None
    lines: dict[str, RaidLine] = field(default_factory=dict)
    pages: dict[str, dict[str, Any]] = field(default_factory=dict)

    def index(self) -> StoredIndex | None:
        return self.stored_index

    def raids(self) -> list[RaidLine]:
        return sorted(self.lines.values(), key=lambda r: r.raid_date, reverse=True)

    def raid(self, report_id: str) -> StoredRaid | None:
        line = self.lines.get(report_id)
        return None if line is None else StoredRaid(line, self.pages.get(report_id))

    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> None:
        self.stored_index = StoredIndex(generated_at, bosses)
        kept = {r.report_id: r for r in raids}
        self.pages = {k: v for k, v in self.pages.items() if k in kept}
        self.lines = {
            k: RaidLine(
                r.report_id, r.raid_date, r.weekday, r.summary, self.lines[k].page_version if k in self.lines else None
            )
            for k, r in kept.items()
        }

    def save_page(self, report_id: str, version: int, page: dict[str, Any]) -> bool:
        line = self.lines.get(report_id)
        if line is None:
            return False
        self.lines[report_id] = RaidLine(line.report_id, line.raid_date, line.weekday, line.summary, version)
        self.pages[report_id] = page
        return True
