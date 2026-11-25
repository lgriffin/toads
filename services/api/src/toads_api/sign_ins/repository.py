"""Where sign-ins live. SignInService only talks to the SignInRepository protocol; the hub-db backed implementation is
`sql.SqlSignInRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SignInRecord:
    """One sign-in, with the raid nights the member was on at that moment."""

    member_id: int
    at: datetime
    raid_days: tuple[str, ...]


@dataclass(frozen=True)
class MemberRecord:
    """A member the hub knows: the raid nights their roles put them on now (empty for none, or not known yet) and when
    they last signed in (None: never)."""

    member_id: int
    raid_days: tuple[str, ...]
    signed_in_at: datetime | None


class SignInRepository(Protocol):
    def between(self, start: datetime, end: datetime) -> list[SignInRecord]:
        """Sign-ins from `start` (included) to `end` (excluded), oldest first."""
        ...

    def members(self) -> list[MemberRecord]: ...


@dataclass
class InMemorySignInRepository:
    """For service tests."""

    sign_ins: list[SignInRecord] = field(default_factory=list)
    known: list[MemberRecord] = field(default_factory=list)

    def between(self, start: datetime, end: datetime) -> list[SignInRecord]:
        return sorted((s for s in self.sign_ins if start <= s.at < end), key=lambda s: s.at)

    def members(self) -> list[MemberRecord]:
        return list(self.known)
