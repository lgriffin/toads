"""Where the Logs pages live. LogService only talks to the LogRepository protocol; the hub-db backed implementation is
`sql.SqlLogRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol

# What save_page did: stored it, the raid is not in the list, or a newer list wants a different build of it.
Saved = Literal["saved", "unlisted", "superseded"]


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
    # The worker's hash of the analysis its latest list built; None when that build could not read the raid.
    want_hash: str | None = None
    # The worker's hash of the analysis the hub holds.
    page_hash: str | None = None


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
    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> bool:
        """Keep exactly these raids (with any analysis already held for them) and this boss history, in one step with
        the check that no newer list is stored; False, changing nothing, when one is. A raid's `want_hash` replaces
        the stored one only when it is set."""
        ...

    def save_page(self, report_id: str, version: int, page: dict[str, Any], page_hash: str) -> Saved:
        """Store a raid's analysis unless the raid is not in the list or the list wants another build of it."""
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

    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> bool:
        if self.stored_index is not None and generated_at < self.stored_index.generated_at:
            return False
        self.stored_index = StoredIndex(generated_at, bosses)
        kept = {r.report_id: r for r in raids}
        self.pages = {k: v for k, v in self.pages.items() if k in kept}
        lines = {}
        for k, r in kept.items():
            held = self.lines.get(k)
            lines[k] = replace(
                r,
                page_version=held.page_version if held else None,
                page_hash=held.page_hash if held else None,
                want_hash=r.want_hash or (held.want_hash if held else None),
            )
        self.lines = lines
        return True

    def save_page(self, report_id: str, version: int, page: dict[str, Any], page_hash: str) -> Saved:
        line = self.lines.get(report_id)
        if line is None:
            return "unlisted"
        if line.want_hash is not None and line.want_hash != page_hash:
            return "superseded"
        self.lines[report_id] = replace(line, page_version=version, page_hash=page_hash)
        self.pages[report_id] = page
        return "saved"
