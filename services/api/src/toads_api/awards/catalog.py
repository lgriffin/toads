"""Every award the hub can give. The web app's artwork and names live in apps/web (static/logos/, src/lib/milestones.ts
for milestones and achievements, src/lib/toads.ts for titles); test_awards.py fails when this list and theirs drift
apart."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class AwardKind(enum.StrEnum):
    # Attendance, Raider of the Month and the Classic Fresh / TBC histories.
    MILESTONE = "milestone"
    # In-game achievements, Classic style.
    ACHIEVEMENT = "achievement"
    # A job a member does for the guild; shown with their rank toad.
    TITLE = "title"
    # Raider of the Week and the weekly piss-takes (Sunder King, Floor Inspector, ...), given after each raid week.
    HONOUR = "honour"


@dataclass(frozen=True)
class Award:
    id: str
    name: str
    kind: AwardKind
    # Given for a month ("YYYY-MM") and so held once per month.
    monthly: bool = False
    # Given for an ISO week ("YYYY-Www") and so held once per week. Every other award is held once.
    weekly: bool = False


def _kind(kind: AwardKind, *pairs: tuple[str, str]) -> list[Award]:
    return [Award(award_id, name, kind) for award_id, name in pairs]


_MILESTONE, _ACHIEVEMENT, _TITLE = AwardKind.MILESTONE, AwardKind.ACHIEVEMENT, AwardKind.TITLE


def _honours(*pairs: tuple[str, str]) -> list[Award]:
    return [Award(award_id, name, AwardKind.HONOUR, weekly=True) for award_id, name in pairs]


AWARDS: dict[str, Award] = {
    a.id: a
    for a in [
        *_kind(
            _MILESTONE,
            ("raids-10", "10 Raids"),
            ("raids-20", "20 Raids"),
            ("raids-50", "50 Raids"),
            ("raids-100", "100 Raids"),
        ),
        Award("raider-of-the-month", "Raider of the Month", _MILESTONE, monthly=True),
        *_kind(_MILESTONE, ("veteran-fresh", "Classic Fresh"), ("veteran-tbc", "TBC Veteran")),
        *_kind(
            _ACHIEVEMENT,
            ("level-60", "Level 60"),
            ("alt-60", "Sixty Alt"),
            ("level-70", "Level 70"),
            ("epic-mount", "Epic Mount"),
            ("flying-mount", "Taking Flight"),
            ("dungeon-set", "Dungeon Set"),
            ("full-tier", "Full Tier"),
            ("legendary", "Legendary"),
            ("master-crafter", "Master Crafter"),
            ("master-angler", "Master Angler"),
            ("chef", "Chef"),
            ("thousand-gold", "1,000 Gold"),
            ("pvp-rank-10", "Rank 10"),
            ("pvp-rank-14", "Rank 14"),
            ("flag-runner", "Flag Runner"),
            ("tarren-mill", "Tarren Mill"),
            ("scarab-lord", "Scarab Lord"),
            ("dragonslayer", "Dragonslayer"),
            ("firelord", "Firelord"),
            ("blackwing-down", "Blackwing Down"),
            ("cthun-down", "C’Thun Down"),  # noqa: RUF001 (the web app writes it with a typographic apostrophe)
            ("lich-slayer", "Lich Slayer"),
            ("serpent-slayer", "Serpentshrine"),
            ("illidan-down", "Illidan Down"),
            ("attuned", "Attuned"),
            ("wipe-veteran", "Wipe Veteran"),
            ("always-flasked", "Always Flasked"),
            ("generous", "Generous"),
            ("pond-builder", "Pond Builder"),
            ("voice-regular", "Voice Regular"),
            ("hardcore", "Hardcore"),
            ("exalted", "Exalted"),
        ),
        *_kind(_TITLE, ("banker", "Banker"), ("developer", "Developer"), ("discord-admin", "Discord Admin")),
        *_honours(
            ("raider-of-the-week", "Raider of the Week"),
            ("sunder-king", "Sunder King"),
            ("best-interrupt", "Best Interrupt"),
            ("floor-inspector", "Floor Inspector"),
            ("stood-in-fire", "Stood in Fire"),
            ("jumped-the-gun", "Jumped the Gun"),
            ("brew-break", "Brew Break"),
            ("repair-bill", "Repair Bill"),
            ("pet-pull", "Pet Pull"),
            ("wrong-skull", "Wrong Skull"),
            ("bone-dry", "Bone Dry"),
            ("meter-gazer", "Meter Gazer"),
        ),
    ]
}
