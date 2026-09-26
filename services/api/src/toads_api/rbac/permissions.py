"""Hub roles, permissions and the three tiers (global officers > raid-day officers > members).

The matrix mirrors "Identity and RBAC" in the Toads Hub build spec. Change it there first;
the RBAC matrix test is generated from ROLE_PERMISSIONS.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class HubRole(enum.IntEnum):
    MEMBER = 0
    TRIAL = 1
    RAIDER = 2
    OFFICER = 3


class Permission(enum.StrEnum):
    VIEW_GUILD_RAIDS = "view_guild_raids"
    VIEW_OWN_PERFORMANCE = "view_own_performance"
    CLAIM_CHARACTER = "claim_character"
    UPLOAD_SCREENSHOTS = "upload_screenshots"
    VIEW_OTHERS = "view_others"
    VIEW_INSIGHTS = "view_insights"
    SYNC_LOGS = "sync_logs"
    APPROVE_CLAIMS = "approve_claims"


_MEMBER = frozenset({Permission.VIEW_GUILD_RAIDS})
_TRIAL = _MEMBER | {Permission.VIEW_OWN_PERFORMANCE, Permission.CLAIM_CHARACTER}
_RAIDER = _TRIAL | {Permission.UPLOAD_SCREENSHOTS}
_OFFICER = frozenset(Permission)

ROLE_PERMISSIONS: dict[HubRole, frozenset[Permission]] = {
    HubRole.MEMBER: _MEMBER,
    HubRole.TRIAL: _TRIAL,
    HubRole.RAIDER: _RAIDER,
    HubRole.OFFICER: _OFFICER,
}


@dataclass(frozen=True)
class Principal:
    """Who is calling, resolved from Discord roles at login / role refresh. Never from the request body."""

    member_id: int
    global_officer: bool = False
    day_roles: dict[str, HubRole] = field(default_factory=dict)

    def role_for(self, raid_day: str | None) -> HubRole:
        if self.global_officer:
            return HubRole.OFFICER
        if raid_day is None:
            # Guild-wide routes: the member's best non-officer standing on any day.
            # Officer powers are always held for a specific day.
            return min(max(self.day_roles.values(), default=HubRole.MEMBER), HubRole.RAIDER)
        return self.day_roles.get(raid_day, HubRole.MEMBER)


def can(principal: Principal, permission: Permission, raid_day: str | None = None) -> bool:
    return permission in ROLE_PERMISSIONS[principal.role_for(raid_day)]
