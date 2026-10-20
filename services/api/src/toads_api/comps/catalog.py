"""The classes and specs a member can raid as and an officer can seat in a comp. The web app keeps the same list in
`apps/web/src/lib/comp.ts`; `test_comps.py` keeps the two in step. Ids are stored, so never rename one."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Role(enum.StrEnum):
    TANK = "tank"
    HEALER = "healer"
    MELEE = "melee"
    RANGED = "ranged"


@dataclass(frozen=True)
class Spec:
    id: str
    wow_class: str
    name: str
    role: Role


def _specs(wow_class: str, *specs: tuple[str, str, Role]) -> list[Spec]:
    return [Spec(f"{wow_class}-{key}", wow_class, name, role) for key, name, role in specs]


T, H, M, R = Role.TANK, Role.HEALER, Role.MELEE, Role.RANGED

CLASSES: dict[str, str] = {
    "warrior": "Warrior",
    "paladin": "Paladin",
    "hunter": "Hunter",
    "rogue": "Rogue",
    "priest": "Priest",
    "shaman": "Shaman",
    "mage": "Mage",
    "warlock": "Warlock",
    "druid": "Druid",
}

SPECS: dict[str, Spec] = {
    s.id: s
    for s in [
        *_specs("warrior", ("arms", "Arms", M), ("fury", "Fury", M), ("protection", "Protection", T)),
        *_specs("paladin", ("holy", "Holy", H), ("protection", "Protection", T), ("retribution", "Retribution", M)),
        *_specs(
            "hunter",
            ("beast-mastery", "Beast Mastery", R),
            ("marksmanship", "Marksmanship", R),
            ("survival", "Survival", R),
        ),
        *_specs("rogue", ("assassination", "Assassination", M), ("combat", "Combat", M), ("subtlety", "Subtlety", M)),
        *_specs("priest", ("discipline", "Discipline", H), ("holy", "Holy", H), ("shadow", "Shadow", R)),
        *_specs(
            "shaman",
            ("elemental", "Elemental", R),
            ("enhancement", "Enhancement", M),
            ("restoration", "Restoration", H),
        ),
        *_specs("mage", ("arcane", "Arcane", R), ("fire", "Fire", R), ("frost", "Frost", R)),
        *_specs(
            "warlock",
            ("affliction", "Affliction", R),
            ("demonology", "Demonology", R),
            ("destruction", "Destruction", R),
        ),
        # Feral Combat is one talent tree played two ways, so the cat and the bear are separate seats.
        *_specs(
            "druid",
            ("balance", "Balance", R),
            ("feral", "Feral", M),
            ("guardian", "Guardian", T),
            ("restoration", "Restoration", H),
        ),
    ]
}


def badges_of_spec(spec_id: str) -> tuple[str, ...]:
    """The role badges (`toads_api.role_badges.catalog`) a primary spec earns: its class, and Tank, Healer or Damage."""
    spec = SPECS.get(spec_id)
    if spec is None:
        return ()
    role = {Role.TANK: "tank", Role.HEALER: "healer"}.get(spec.role, "damage")
    return (spec.wow_class, role)


# Raid sizes World of Warcraft: Forever runs, in groups of five.
RAID_SIZES = (10, 20, 40)
GROUP_SIZE = 5
