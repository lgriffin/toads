"""Where member settings live. AccountService only talks to the AccountRepository protocol; the hub-db backed
implementation is `sql.SqlAccountRepository`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class MemberNames:
    """Everything that decides the name a member is shown by."""

    member_id: int
    discord_user_id: int
    discord_name: str
    name_source: str
    name_character_id: int | None
    # Characters the member holds an approved claim on: id -> name.
    characters: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WclKeyRecord:
    """What is known about a saved key without decrypting it."""

    client_id_hint: str
    status: str
    updated_at: datetime
    checked_at: datetime | None


class AccountRepository(Protocol):
    def names(self, member_ids: Iterable[int] | None = None) -> list[MemberNames]: ...
    def set_name(self, member_id: int, source: str, character_id: int | None) -> None: ...

    def wcl_key(self, member_id: int) -> WclKeyRecord | None: ...
    def save_wcl_key(self, member_id: int, client_id: str, client_secret: str) -> WclKeyRecord: ...
    def delete_wcl_key(self, member_id: int) -> bool: ...


@dataclass
class InMemoryAccountRepository:
    """For service tests. Keeps keys in memory as given; never use it outside tests."""

    members: dict[int, MemberNames] = field(default_factory=dict)
    keys: dict[int, tuple[str, str, WclKeyRecord]] = field(default_factory=dict)

    def names(self, member_ids: Iterable[int] | None = None) -> list[MemberNames]:
        wanted = None if member_ids is None else set(member_ids)
        return [m for i, m in sorted(self.members.items()) if wanted is None or i in wanted]

    def set_name(self, member_id: int, source: str, character_id: int | None) -> None:
        m = self.members[member_id]
        self.members[member_id] = MemberNames(
            m.member_id, m.discord_user_id, m.discord_name, source, character_id, m.characters
        )

    def wcl_key(self, member_id: int) -> WclKeyRecord | None:
        entry = self.keys.get(member_id)
        return entry[2] if entry else None

    def save_wcl_key(self, member_id: int, client_id: str, client_secret: str) -> WclKeyRecord:
        record = WclKeyRecord(client_id[-4:], "unverified", datetime.now(UTC), None)
        self.keys[member_id] = (client_id, client_secret, record)
        return record

    def delete_wcl_key(self, member_id: int) -> bool:
        return self.keys.pop(member_id, None) is not None
