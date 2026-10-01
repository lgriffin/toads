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
    # Community layer: recruitment, curated posts, highlight reels and spotlights.
    APPLY = "apply"
    SUBMIT_HIGHLIGHT = "submit_highlight"
    MANAGE_RECRUITMENT = "manage_recruitment"
    MANAGE_POSTS = "manage_posts"
    MANAGE_HIGHLIGHTS = "manage_highlights"
    # Guild bank (ToadsBank, docs/bank.md). ToadsBank still applies a source's audience and its managers list.
    VIEW_BANK = "view_bank"
    REQUEST_BANK_ITEMS = "request_bank_items"
    IMPORT_BANK_SNAPSHOT = "import_bank_snapshot"
    MANAGE_BANK = "manage_bank"


# Applicants join the Discord server first, so a plain member (no raid-day role) can apply. Every guild member may see
# the bank and ask it for items; importing snapshots and running the request queue are officers' work.
_MEMBER = frozenset(
    {Permission.VIEW_GUILD_RAIDS, Permission.APPLY, Permission.VIEW_BANK, Permission.REQUEST_BANK_ITEMS}
)
_TRIAL = _MEMBER | {Permission.VIEW_OWN_PERFORMANCE, Permission.CLAIM_CHARACTER}
_RAIDER = _TRIAL | {Permission.UPLOAD_SCREENSHOTS, Permission.SUBMIT_HIGHLIGHT}
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
    display_name: str = ""
    # The member's Discord user id: the identity the hub vouches for to ToadsBank. None only in tests.
    discord_user_id: int | None = None

    @property
    def is_officer(self) -> bool:
        """Holds officer powers anywhere: globally or for at least one raid day."""
        return self.global_officer or HubRole.OFFICER in self.day_roles.values()

    def home_day(self) -> str | None:
        """The raid day this member ranks highest on (config order breaks ties); None without one."""
        if not self.day_roles:
            return None
        return max(self.day_roles.items(), key=lambda item: item[1])[0]

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
