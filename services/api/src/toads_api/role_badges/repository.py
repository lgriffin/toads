"""Where role badges live. RoleBadgeService only talks to the RoleBadgeRepository protocol; the hub-db backed
implementation is `sql.SqlRoleBadgeRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class RoleBadgeLink:
    discord_role_id: int
    badge_id: str
    role_name: str
    added_by: int | None
    added_at: datetime


class DuplicateLinkError(Exception):
    """The role already earns this badge."""


class RoleBadgeRepository(Protocol):
    def links(self) -> list[RoleBadgeLink]: ...
    def add(self, discord_role_id: int, badge_id: str, role_name: str, by: int) -> RoleBadgeLink: ...
    def remove(self, discord_role_id: int, badge_id: str, by: int) -> bool: ...


@dataclass
class InMemoryRoleBadgeRepository:
    """For service tests."""

    rows: list[RoleBadgeLink] = field(default_factory=list)

    def links(self) -> list[RoleBadgeLink]:
        return list(self.rows)

    def add(self, discord_role_id: int, badge_id: str, role_name: str, by: int) -> RoleBadgeLink:
        if any((r.discord_role_id, r.badge_id) == (discord_role_id, badge_id) for r in self.rows):
            raise DuplicateLinkError
        row = RoleBadgeLink(discord_role_id, badge_id, role_name, by, datetime.now(UTC))
        self.rows.append(row)
        return row

    def remove(self, discord_role_id: int, badge_id: str, by: int) -> bool:
        kept = [r for r in self.rows if (r.discord_role_id, r.badge_id) != (discord_role_id, badge_id)]
        removed = len(kept) != len(self.rows)
        self.rows = kept
        return removed
