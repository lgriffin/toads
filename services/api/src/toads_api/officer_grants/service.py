"""Rules for officer grants. No RBAC, web framework or storage imports: the routes decide who may call (super admins
alone), the RBAC layer turns a member's grants into officer standing, and the repository decides where grants live."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from toads_api.officer_grants.repository import NewOfficerGrant, OfficerGrantRecord, OfficerGrantRepository

NAME_LIMIT = 100
USERNAME_LIMIT = 32


class OfficerGrantError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class OfficerStanding:
    """What a member's officer grants give them: officer powers on these raid days, or on every day."""

    days: frozenset[str] = frozenset()
    global_officer: bool = False


NO_STANDING = OfficerStanding()


class OfficerGrantService:
    def __init__(self, repo: OfficerGrantRepository, day_ids: Iterable[str]) -> None:
        self._repo = repo
        self._days = frozenset(day_ids)

    def all_grants(self) -> list[OfficerGrantRecord]:
        return self._repo.all()

    def standing(self, discord_user_id: int) -> OfficerStanding:
        """What a member holds right now. A grant for a raid day the config no longer has opens nothing."""
        held = self._repo.held_by(discord_user_id)
        if not held:
            return NO_STANDING
        return OfficerStanding(
            days=frozenset(d for d in held if d is not None and d in self._days), global_officer=None in held
        )

    def grant(
        self, discord_user_id: int, username: str, display_name: str, raid_day: str | None, granted_by: int
    ) -> tuple[OfficerGrantRecord, bool]:
        """Make one member an officer of one raid day (None: a global officer). Granting what is already held returns
        the existing grant; True when the grant is new."""
        if raid_day is not None and raid_day not in self._days:
            raise OfficerGrantError("Unknown raid day", 422)
        if discord_user_id <= 0:
            raise OfficerGrantError("That is not a Discord user id", 422)
        name = display_name.strip()[:NAME_LIMIT] or str(discord_user_id)
        return self._repo.add(
            NewOfficerGrant(discord_user_id, username.strip()[:USERNAME_LIMIT], name, raid_day, granted_by)
        )

    def revoke(self, grant_id: int, revoked_by: int) -> OfficerGrantRecord:
        removed = self._repo.remove(grant_id, revoked_by)
        if removed is None:
            raise OfficerGrantError("No such officer grant", 404)
        return removed
