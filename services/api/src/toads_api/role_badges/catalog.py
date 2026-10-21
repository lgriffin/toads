"""Every badge a super admin can tie to a Discord role. The artwork lives in apps/web/static/logos/ and the web app's
list in src/lib/role-badges.ts; test_role_badges.py fails when this list and theirs drift apart."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleBadge:
    id: str
    name: str
    # The artwork under apps/web/static/logos/, without `.svg`.
    file: str


_CLASSES = ("druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior")
# The races the guild can play on the Horde side in WoW Forever, Skyborne (Windshapers) included.
_RACES = ("orc", "troll", "tauren", "undead", "skyborne")

ROLE_BADGES: dict[str, RoleBadge] = {
    b.id: b
    for b in [
        # The raid nights.
        RoleBadge("wednesday-toad", "Wednesday Toad", "days/wednesday-toad"),
        RoleBadge("thursday-toad", "Thursday Toad", "days/thursday-toad"),
        RoleBadge("sunday-toad", "Sunday Toad", "days/sunday-toad"),
        # Each raid night's officers: tying one makes the role's holders that night's officers (docs/role-badges.md).
        RoleBadge("wednesday-officer", "Wednesday Officer", "ranks/officer"),
        RoleBadge("thursday-officer", "Thursday Officer", "ranks/officer"),
        RoleBadge("sunday-officer", "Sunday Officer", "ranks/officer"),
        # What a member does in the raid.
        RoleBadge("tank", "Tank", "roles/tank"),
        RoleBadge("healer", "Healer", "roles/healer"),
        RoleBadge("damage", "Damage", "roles/damage"),
        # Servers often give a role per class.
        *(RoleBadge(c, c.title(), f"classes/{c}") for c in _CLASSES),
        # And per race.
        *(RoleBadge(r, r.title(), f"races/{r}") for r in _RACES),
    ]
}


def night_badge_id(day_name: str) -> str:
    """The badge of a raid night, from its name in raid_days.yaml: "Thursday" earns "thursday-toad"."""
    return f"{day_name.strip().lower()}-toad"


def night_officer_badge_id(day_name: str) -> str:
    """The badge of a raid night's officers: "Thursday" has "thursday-officer"."""
    return f"{day_name.strip().lower()}-officer"
