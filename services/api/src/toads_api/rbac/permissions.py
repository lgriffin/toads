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
    # Super admins only (docs/admin.md): grant and revoke bank grants, mint and revoke officer tokens.
    MANAGE_GRANTS = "manage_grants"
    # Give and take back members' awards (docs/awards.md). Awards are guild-wide, so only the global tier holds it.
    MANAGE_AWARDS = "manage_awards"
    # Build and lock in a raid day's comps from its roster's specs (docs/comps.md).
    BUILD_COMPS = "build_comps"
    # Super admins only (docs/role-badges.md): say which Discord roles earn which badge toads.
    MANAGE_ROLE_BADGES = "manage_role_badges"
    # Absences (docs/absences.md): a raid day's trials and raiders say which nights they will miss; its officers see
    # them gathered in one place.
    REPORT_ABSENCE = "report_absence"
    VIEW_ABSENCES = "view_absences"
    # The officers' task board for a raid day (docs/officer-board.md): that day's officers and the global tier.
    MANAGE_OFFICER_BOARD = "manage_officer_board"
    # Super admins only (docs/admin.md "Officer grants"): make one Discord member an officer of a raid day, or a global
    # officer, on top of their Discord roles. Nothing grants super admin: that is configuration alone.
    MANAGE_OFFICER_GRANTS = "manage_officer_grants"


# Held by super admins alone, above every Discord role; never by an officer role or a grant.
SUPER_ADMIN_ONLY = frozenset(
    {Permission.MANAGE_GRANTS, Permission.MANAGE_ROLE_BADGES, Permission.MANAGE_OFFICER_GRANTS}
)


# Applicants join the Discord server first, so a plain member (no raid-day role) can apply. Every guild member may see
# the bank and ask it for items; importing snapshots and running the request queue are officers' work.
_MEMBER = frozenset(
    {Permission.VIEW_GUILD_RAIDS, Permission.APPLY, Permission.VIEW_BANK, Permission.REQUEST_BANK_ITEMS}
)
_TRIAL = _MEMBER | {Permission.VIEW_OWN_PERFORMANCE, Permission.CLAIM_CHARACTER, Permission.REPORT_ABSENCE}
_RAIDER = _TRIAL | {Permission.UPLOAD_SCREENSHOTS, Permission.SUBMIT_HIGHLIGHT}
_OFFICER = frozenset(Permission) - SUPER_ADMIN_ONLY

# Permissions a super admin may grant one Discord user without making them an officer (docs/bank.md "Grants"):
# the bank's upkeep. Officers hold them already through their role, so a grant only ever adds to a non-officer.
GRANTABLE = frozenset({Permission.IMPORT_BANK_SNAPSHOT, Permission.MANAGE_BANK})

ROLE_PERMISSIONS: dict[HubRole, frozenset[Permission]] = {
    HubRole.MEMBER: _MEMBER,
    HubRole.TRIAL: _TRIAL,
    HubRole.RAIDER: _RAIDER,
    HubRole.OFFICER: _OFFICER,
}


@dataclass(frozen=True)
class Principal:
    """Who is calling, resolved from Discord roles at login / role refresh plus the officer grants a super admin gave
    them (read per request). Never from the request body."""

    member_id: int
    global_officer: bool = False
    day_roles: dict[str, HubRole] = field(default_factory=dict)
    display_name: str = ""
    # The member's Discord user id: the identity the hub vouches for to ToadsBank. None only in tests.
    discord_user_id: int | None = None
    # The member's Discord username (account handle, not the server nickname). "" in tests and old sessions.
    discord_username: str = ""
    # Every Discord role the member holds in the server, for the badges a super admin ties to roles
    # (docs/role-badges.md). Never a source of permissions: those come from day_roles and global_officer alone.
    discord_role_ids: frozenset[int] = frozenset()
    # Bank grants this member holds, read from the database on every request (never cached with the roles), so a
    # revoke takes effect on their next call: (permission, raid day), where a None day covers every raid day.
    grants: frozenset[tuple[Permission, str | None]] = frozenset()
    # Above the global tier (docs/admin.md): named by Discord user id in TOADS_SUPER_ADMIN_IDS, never by a role or the
    # database, so nothing in the app can make someone one. A super admin is always a global officer too.
    super_admin: bool = False
    # Made a super admin by TOADS_BREAK_GLASS_ADMIN_ID, whatever their roles or the super admin list say. Shown in
    # /api/session and on the bank page, and every mutating call they make is audit-logged as "break_glass".
    break_glass: bool = False

    def __post_init__(self) -> None:
        if self.break_glass and not self.super_admin:
            object.__setattr__(self, "super_admin", True)
        if self.super_admin and not self.global_officer:
            object.__setattr__(self, "global_officer", True)

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

    def granted(self, permission: Permission, raid_day: str) -> bool:
        """A grant covers this raid day: one for that day, or one for every day. Grants hold only GRANTABLE
        permissions and only ever on a raid day's routes, never on guild-wide (global tier) ones."""
        return permission in GRANTABLE and ((permission, raid_day) in self.grants or (permission, None) in self.grants)

    def unbound(self, permission: Permission) -> bool:
        """Works every bank under any raid day's URL: the global tier, or a grant with no raid day."""
        return self.global_officer or (permission in GRANTABLE and (permission, None) in self.grants)


def can(principal: Principal, permission: Permission, raid_day: str | None = None) -> bool:
    if permission in SUPER_ADMIN_ONLY:
        return principal.super_admin
    if permission in ROLE_PERMISSIONS[principal.role_for(raid_day)]:
        return True
    # Officers inherit every grantable permission through their role; a grant adds it for one more member, and only
    # on a raid day taken from the route's path.
    return raid_day is not None and principal.granted(permission, raid_day)
