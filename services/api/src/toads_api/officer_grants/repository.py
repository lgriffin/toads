"""Where officer grants live. OfficerGrantService only talks to the OfficerGrantRepository protocol; the hub-db backed
implementation is `sql.SqlOfficerGrantRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class NewOfficerGrant:
    discord_user_id: int
    username: str
    display_name: str
    # None: a global officer, on every raid day.
    raid_day: str | None
    # The member id of the super admin granting it.
    granted_by: int


@dataclass(frozen=True)
class OfficerGrantRecord:
    id: int
    discord_user_id: int
    username: str
    display_name: str
    raid_day: str | None
    granted_by: int | None
    granted_by_name: str | None
    granted_at: datetime


class OfficerGrantRepository(Protocol):
    def all(self) -> list[OfficerGrantRecord]: ...

    def held_by(self, discord_user_id: int) -> list[str | None]:
        """The raid days a member is granted officer powers on; None for a global officer grant."""
        ...

    def add(self, grant: NewOfficerGrant) -> tuple[OfficerGrantRecord, bool]:
        """Store a grant, or return the one already held for the same user and raid day. True when new."""
        ...

    def remove(self, grant_id: int, revoked_by: int) -> OfficerGrantRecord | None:
        """Delete a grant; None when there is no such grant."""
        ...


@dataclass
class InMemoryOfficerGrantRepository:
    """For service tests; never use it outside tests."""

    grants: dict[int, OfficerGrantRecord] = field(default_factory=dict)
    revoked: list[tuple[int, int]] = field(default_factory=list)

    def all(self) -> list[OfficerGrantRecord]:
        return [self.grants[i] for i in sorted(self.grants)]

    def held_by(self, discord_user_id: int) -> list[str | None]:
        return [g.raid_day for g in self.all() if g.discord_user_id == discord_user_id]

    def add(self, grant: NewOfficerGrant) -> tuple[OfficerGrantRecord, bool]:
        for g in self.grants.values():
            if (g.discord_user_id, g.raid_day) == (grant.discord_user_id, grant.raid_day):
                return g, False
        record = OfficerGrantRecord(
            id=max(self.grants, default=0) + 1,
            discord_user_id=grant.discord_user_id,
            username=grant.username,
            display_name=grant.display_name,
            raid_day=grant.raid_day,
            granted_by=grant.granted_by,
            granted_by_name=None,
            granted_at=datetime.now(UTC),
        )
        self.grants[record.id] = record
        return record, True

    def remove(self, grant_id: int, revoked_by: int) -> OfficerGrantRecord | None:
        record = self.grants.pop(grant_id, None)
        if record is not None:
            self.revoked.append((grant_id, revoked_by))
        return record
