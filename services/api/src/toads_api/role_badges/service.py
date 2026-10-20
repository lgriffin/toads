"""Rules for role badges. No RBAC, web framework, Discord or storage imports: the routes decide who may call and
read Discord, and the repository decides where things live."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from toads_api.role_badges.catalog import ROLE_BADGES, RoleBadge, night_badge_id, night_officer_badge_id
from toads_api.role_badges.repository import DuplicateLinkError, RoleBadgeLink, RoleBadgeRepository


class RoleBadgeError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class LinkView:
    """A role and the badge it earns, as the admin console lists it."""

    discord_role_id: int
    role_name: str
    badge: RoleBadge
    added_at: datetime


class RoleBadgeService:
    def __init__(self, repo: RoleBadgeRepository) -> None:
        self.repo = repo

    def _live(self) -> list[RoleBadgeLink]:
        # A badge retired from the catalogue stays stored but earns nothing.
        return [r for r in self.repo.links() if r.badge_id in ROLE_BADGES]

    def links(self) -> list[LinkView]:
        """Every role tied to a badge, in catalogue order, then by role name."""
        order = {badge_id: i for i, badge_id in enumerate(ROLE_BADGES)}
        rows = sorted(self._live(), key=lambda r: (order[r.badge_id], r.role_name.lower(), r.discord_role_id))
        return [LinkView(r.discord_role_id, r.role_name, ROLE_BADGES[r.badge_id], r.added_at) for r in rows]

    def night_roles(self, nights: Iterable[tuple[str, str]]) -> dict[str, set[int]]:
        """The Discord roles tied to each raid night's badge, by day id, for `(day id, day name)` pairs: the Thursday
        Toad badge is "thursday-toad". Holding one of them puts a member on that night's team."""
        return self.night_badge_roles(nights)[0]

    def night_officer_roles(self, nights: Iterable[tuple[str, str]]) -> dict[str, set[int]]:
        """The Discord roles tied to each raid night's officer badge ("thursday-officer"), by day id. Holding one of
        them makes a member that night's officer."""
        return self.night_badge_roles(nights)[1]

    def night_badge_roles(self, nights: Iterable[tuple[str, str]]) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
        """`night_roles` and `night_officer_roles` from one read of the ties, for building a principal per request."""
        tied: dict[str, set[int]] = {}
        for r in self._live():
            tied.setdefault(r.badge_id, set()).add(r.discord_role_id)
        pairs = list(nights)

        def by_night(badge_of: Callable[[str], str]) -> dict[str, set[int]]:
            return {day_id: roles for day_id, name in pairs if (roles := tied.get(badge_of(name)))}

        return by_night(night_badge_id), by_night(night_officer_badge_id)

    def earned(self, discord_role_ids: Iterable[int], also: Iterable[str] = ()) -> list[RoleBadge]:
        """The badges a member's Discord roles earn, plus the badge ids in `also` (the class and role their primary
        spec earns), each once, in catalogue order."""
        held = set(discord_role_ids)
        ids = {r.badge_id for r in self._live() if r.discord_role_id in held} | set(also)
        return [b for b in ROLE_BADGES.values() if b.id in ids]

    def tie(self, discord_role_id: int, role_name: str, badge_id: str, by: int) -> LinkView:
        badge = ROLE_BADGES.get(badge_id)
        if badge is None:
            raise RoleBadgeError("Unknown badge", status=422)
        try:
            row = self.repo.add(discord_role_id, badge_id, role_name.strip()[:100], by)
        except DuplicateLinkError:
            raise RoleBadgeError(f"That role already earns {badge.name}", status=409) from None
        return LinkView(row.discord_role_id, row.role_name, badge, row.added_at)

    def untie(self, discord_role_id: int, badge_id: str, by: int) -> None:
        if not self.repo.remove(discord_role_id, badge_id, by):
            raise RoleBadgeError("That role does not earn that badge", status=404)
