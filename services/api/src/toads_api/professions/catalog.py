"""The professions a member can list, with their specialisations. The web app keeps the same list in
`apps/web/src/lib/professions.ts`; `test_professions.py` keeps the two in step. Ids are stored, so never rename one."""

from __future__ import annotations

from dataclasses import dataclass

# The highest skill a profession reaches.
MAX_SKILL = 375


@dataclass(frozen=True)
class Profession:
    id: str
    name: str
    # Secondary professions (cooking, first aid, fishing) do not count against the two primary ones a character has.
    secondary: bool = False
    # (id, name) of the specialisations a crafter of this profession may pick; ids are unique within the profession.
    specialisations: tuple[tuple[str, str], ...] = ()


PROFESSIONS: dict[str, Profession] = {
    p.id: p
    for p in [
        Profession(
            "alchemy",
            "Alchemy",
            specialisations=(
                ("elixir", "Elixir Master"),
                ("potion", "Potion Master"),
                ("transmute", "Transmutation Master"),
            ),
        ),
        Profession(
            "blacksmithing",
            "Blacksmithing",
            specialisations=(
                ("armorsmith", "Armorsmith"),
                ("weaponsmith", "Weaponsmith"),
                ("axesmith", "Master Axesmith"),
                ("hammersmith", "Master Hammersmith"),
                ("swordsmith", "Master Swordsmith"),
            ),
        ),
        Profession("enchanting", "Enchanting"),
        Profession("engineering", "Engineering", specialisations=(("gnomish", "Gnomish"), ("goblin", "Goblin"))),
        Profession("jewelcrafting", "Jewelcrafting"),
        Profession(
            "leatherworking",
            "Leatherworking",
            specialisations=(("dragonscale", "Dragonscale"), ("elemental", "Elemental"), ("tribal", "Tribal")),
        ),
        Profession(
            "tailoring",
            "Tailoring",
            specialisations=(("mooncloth", "Mooncloth"), ("shadoweave", "Shadoweave"), ("spellfire", "Spellfire")),
        ),
        Profession("herbalism", "Herbalism"),
        Profession("mining", "Mining"),
        Profession("skinning", "Skinning"),
        Profession("cooking", "Cooking", secondary=True),
        Profession("first-aid", "First Aid", secondary=True),
        Profession("fishing", "Fishing", secondary=True),
    ]
}
