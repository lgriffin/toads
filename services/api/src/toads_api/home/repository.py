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


class HomeRepository(Protocol):
    def layout(self, member_id: int) -> list[StoredWidget] | None: ...
    def save_layout(self, member_id: int, widgets: list[StoredWidget]) -> None: ...
    def delete_layout(self, member_id: int) -> bool: ...

    def analyzer_page(self) -> StoredPage | None: ...
    def save_analyzer_page(self, page: StoredPage) -> None: ...


@dataclass
class InMemoryHomeRepository:
    """For service tests."""

    layouts: dict[int, list[StoredWidget]] = field(default_factory=dict)
    page: StoredPage | None = None

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
