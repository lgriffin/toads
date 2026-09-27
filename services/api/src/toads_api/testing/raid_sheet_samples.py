"""Small CBA and RPB tabs laid out like the real sheets, as the worker posts them (first non-empty row as headers).

Cut down from the guild's sheets for the 2026-09-16 Black Temple / Hyjal run; names are made up.
"""

from __future__ import annotations

from typing import Any

TITLE = "BT / Hyjal (BT in 1:48:32, MH in 1:08:40)"
REPORT = "2bNJMG9AfDnmxKYh"
VALID = "Is the log a valid log (also are the trash requirements met)?"
WEBHOOK = "https://discord.com/api/webhooks/1234567890/abcDEF-ghi_jkl"


def _tab(name: str, grid: list[list[str]]) -> dict[str, Any]:
    return {"tab": name, "headers": grid[0], "rows": grid[1:]}


def cba_tabs(when: str = "September 23, 2026 19:32:26") -> list[dict[str, Any]]:
    head = [["", "title ", TITLE], ["", "zone ", "Black Temple"], ["", "date ", when]]
    return [
        _tab(
            "Instructions",
            [
                ["3.", "", "", "", f"https://fresh.warcraftlogs.com/reports/{REPORT}"],
                ["5.", "", "", "", WEBHOOK, "", "", "", "runner@example.com"],
            ],
        ),
        _tab(
            "buff consumables",
            [
                *head,
                ["", "start - end (optional)"],
                ["0", "", "total average (excl. Scrolls)", "Elixir or Flask", "Battle Elixir", "Flask", "Food Buff"],
                ["", "Hopscotch", "0.9433333333", "1", "1.0", "0.0", "0.89"],
                ["", "Ribbit", "0.74", "0.86", "0.94", "0.0", "0.89"],
                ["", "Croak", "-"],
            ],
        ),
        _tab(
            "gear issues",
            [
                ["", "", "", "yes", "list players with no issues?", "title ", TITLE],
                ["", "", "", "no", "exclude Mother Shahraz", "zone ", "Black Temple"],
                ["", "", "", "", "", "date ", when],
                ["", "", "name", "", "", "Item [Issue]", "Item [Issue]"],
                ["", "15138", "Onyxia Scale Cloak", "", "Hopscotch", "Boots [no enchant]", "Gloves [no gem]"],
                ["", "9449", "Manual Crowd Pummeler", "", "Ribbit", "-----------"],
                ["", "30318", "Netherstrand Longbow"],
                ["", "", "", "< enter custom lines below here"],
            ],
        ),
        _tab(
            "drums",
            [
                ["", "", "", "", "title ", TITLE],
                ["", "", "", "", "date ", when],
                ["", "⌀ = average buffs per drum", "# of battle drums", "# of war drums", "# of restoration drums"],
                ["", "Ribbit", "22 (⌀ 2.36)", "", "3 (⌀ 1.00)", "1", "22", "2.36"],
            ],
        ),
        _tab(
            "validate",
            [
                ["", "", "", "", "", "", "", "title ", TITLE],
                ["", "", "", "", "", "", "", "date ", when],
                ["IDs", "", "name", "", "", "", "", VALID, "", "", "yes"],
                ["", "", "", "", "", "", "empty", "total number of characters used:", "", "25"],
            ],
        ),
    ]


def rpb_tabs(extra_potion: str = "") -> list[dict[str, Any]]:
    return [
        _tab(
            "General",
            [
                ["", "Hopscotch", "Ribbit"],
                ["Consumables"],
                ["Drums of Battle", "", "22"],
                ["Haste Potion", "9", "3"],
                ["Flame Cap"],
                ["Super Mana Potion equivalents", extra_potion, "4"],
                ["Damage absorbed"],
                ["Major Shadow Protection Potion", "3868"],
                ["Interrupted spells"],
                ["# of interrupted spells", "1", "3"],
            ],
        ),
        _tab(
            "Tank",
            [
                ["", "Hopscotch"],
                ["Stats and Miscellanous"],
                ["# of deaths in total (just on trash)", "3 (0)"],
                ["Total (partly) avoidable damage taken", "274846.0"],
                ["", "0.79"],
            ],
        ),
        _tab(
            "Caster",
            [
                ["", "Ribbit"],
                ["# of deaths in total (just on trash)", "6 (1)"],
                ["Total (partly) avoidable damage taken", "80107"],
            ],
        ),
        _tab("Caster - casts", [["", "Mages"], ["# of deaths in total (just on trash)", "99"]]),
    ]
