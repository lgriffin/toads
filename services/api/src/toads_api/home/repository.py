"""Where home layouts live. HomeService only talks to the HomeRepository protocol; the hub-db backed implementation is
`sql.SqlHomeRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


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


class HomeRepository(Protocol):
    def layout(self, member_id: int) -> list[StoredWidget] | None: ...
    def save_layout(self, member_id: int, widgets: list[StoredWidget]) -> None: ...
    def delete_layout(self, member_id: int) -> bool: ...

    def analyzer_page(self) -> StoredPage | None: ...
    def save_analyzer_page(self, page: StoredPage) -> None: ...

    def performance_page(self) -> StoredPerformance | None: ...
    def save_performance_page(self, page: StoredPerformance) -> None: ...
    def member_characters(self, member_id: int) -> MemberCharacters | None: ...


@dataclass
class InMemoryHomeRepository:
    """For service tests."""

    layouts: dict[int, list[StoredWidget]] = field(default_factory=dict)
    page: StoredPage | None = None
    performance: StoredPerformance | None = None
    characters: dict[int, MemberCharacters] = field(default_factory=dict)

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

    def performance_page(self) -> StoredPerformance | None:
        return self.performance

    def save_performance_page(self, page: StoredPerformance) -> None:
        self.performance = page

    def member_characters(self, member_id: int) -> MemberCharacters | None:
        return self.characters.get(member_id)
