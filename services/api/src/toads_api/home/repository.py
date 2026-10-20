"""Where home layouts live. HomeService only talks to the HomeRepository protocol; the hub-db backed implementation is
`sql.SqlHomeRepository`."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Protocol


def fold(name: str) -> str:
    """Case- and width-insensitive, as claims compare names; accents still count."""
    return unicodedata.normalize("NFKC", name).strip().casefold()


@dataclass(frozen=True)
class StoredWidget:
    """One entry of a saved layout, in display order. Hidden widgets are kept so a later catalogue addition can tell
    "hidden on purpose" from "new since the member last saved"."""

    id: str
    shown: bool


@dataclass(frozen=True)
class StoredPage:
    """The analyzer's home page as the worker published it: guild-wide, one at a time."""

    version: int
    generated_at: str
    widgets: list[dict[str, Any]]


@dataclass(frozen=True)
class StoredPerformance:
    """The worker's performance page (toads_worker.jobs.performance): the last raid and every player's entry in it."""

    version: int
    generated_at: str
    raid: dict[str, Any] | None
    players: list[dict[str, Any]]


@dataclass(frozen=True)
class StoredBadges:
    """The worker's badge page (toads_worker.jobs.badges): every raider's badges, as wcl_app.badges builds them."""

    version: int
    generated_at: str
    players: list[dict[str, Any]]


@dataclass(frozen=True)
class StoredCharacterPage:
    """One character's page as the worker built it (toads_worker.jobs.characters, wcl_app.character_pages)."""

    version: int
    generated_at: str
    page: dict[str, Any]


@dataclass(frozen=True)
class MemberCharacters:
    """The names a member's own numbers may be under."""

    # Their Discord server nickname, as refreshed at sign-in.
    nickname: str
    # The approved character they chose to go by, if any.
    chosen: str | None
    # Characters they hold an approved claim on.
    approved: list[str]
    # Case-folded names another member claims (approved or pending): never shown to anyone else.
    claimed_by_others: frozenset[str]
    # Another member goes by the same server nickname, so the nickname alone cannot say whose character it is.
    nickname_shared: bool = False


class HomeRepository(Protocol):
    def layout(self, member_id: int) -> list[StoredWidget] | None: ...
    def save_layout(self, member_id: int, widgets: list[StoredWidget]) -> None: ...
    def delete_layout(self, member_id: int) -> bool: ...

    def analyzer_page(self) -> StoredPage | None: ...
    def save_analyzer_page(self, page: StoredPage) -> None: ...
    def night_page(self, day: str) -> StoredPage | None: ...
    def save_night_page(self, day: str, page: StoredPage) -> None: ...

    def performance_page(self) -> StoredPerformance | None: ...
    def save_performance_page(self, page: StoredPerformance) -> None: ...
    def badge_page(self) -> StoredBadges | None: ...
    def save_badge_page(self, page: StoredBadges) -> bool:
        """Keep `page` unless the stored one is newer, checked in the same transaction as the write. Returns
        whether it was kept."""
        ...

    def member_characters(self, member_id: int) -> MemberCharacters | None: ...

    def character_names(self) -> list[str]:
        """Every name a member may go by: approved claims and server nicknames, the characters the worker builds a
        page for."""
        ...

    def character_page(self, name: str) -> StoredCharacterPage | None: ...

    def character_pages_generated_at(self) -> str | None:
        """When the stored character pages were built; None before the worker has published any."""
        ...

    def save_character_pages(self, version: int, generated_at: str, pages: list[dict[str, Any]]) -> bool:
        """Replace every character page with `pages` unless the stored ones are newer, in one transaction. Returns
        whether they were kept."""
        ...


@dataclass
class InMemoryHomeRepository:
    """For service tests."""

    layouts: dict[int, list[StoredWidget]] = field(default_factory=dict)
    page: StoredPage | None = None
    nights: dict[str, StoredPage] = field(default_factory=dict)
    performance: StoredPerformance | None = None
    badges: StoredBadges | None = None
    characters: dict[int, MemberCharacters] = field(default_factory=dict)
    character_pages: dict[str, StoredCharacterPage] = field(default_factory=dict)
    character_build: str | None = None

    def layout(self, member_id: int) -> list[StoredWidget] | None:
        found = self.layouts.get(member_id)
        return None if found is None else list(found)

    def save_layout(self, member_id: int, widgets: list[StoredWidget]) -> None:
        self.layouts[member_id] = list(widgets)

    def delete_layout(self, member_id: int) -> bool:
        return self.layouts.pop(member_id, None) is not None

    def analyzer_page(self) -> StoredPage | None:
        return self.page

    def save_analyzer_page(self, page: StoredPage) -> None:
        self.page = page

    def night_page(self, day: str) -> StoredPage | None:
        return self.nights.get(day)

    def save_night_page(self, day: str, page: StoredPage) -> None:
        self.nights[day] = page

    def performance_page(self) -> StoredPerformance | None:
        return self.performance

    def save_performance_page(self, page: StoredPerformance) -> None:
        self.performance = page

    def badge_page(self) -> StoredBadges | None:
        return self.badges

    def save_badge_page(self, page: StoredBadges) -> bool:
        if self.badges is not None and page.generated_at < self.badges.generated_at:
            return False
        self.badges = page
        return True

    def member_characters(self, member_id: int) -> MemberCharacters | None:
        return self.characters.get(member_id)

    def character_names(self) -> list[str]:
        names = (n for c in self.characters.values() for n in (c.nickname, *c.approved) if n.strip())
        by_key = {fold(n): n.strip() for n in names}
        return sorted(by_key.values(), key=str.casefold)

    def character_page(self, name: str) -> StoredCharacterPage | None:
        return self.character_pages.get(fold(name))

    def character_pages_generated_at(self) -> str | None:
        return self.character_build

    def save_character_pages(self, version: int, generated_at: str, pages: list[dict[str, Any]]) -> bool:
        if self.character_build is not None and generated_at < self.character_build:
            return False
        self.character_build = generated_at
        self.character_pages = {fold(str(p["name"])): StoredCharacterPage(version, generated_at, p) for p in pages}
        return True
