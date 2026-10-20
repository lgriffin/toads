"""Reading a Raid-Helper export (https://raid-helper.dev, the Discord sign-up bot) into class and spec ids from our
catalogue. Two shapes are read: the composition tool's export (`slots`) and an event's sign-ups (`signUps`). Nothing
here touches storage or Discord; the import route matches each Discord user id to a hub member.

Raid-Helper names a spec by the name its emoji shows, which for TBC is not always ours: tanks sit under a pseudo-class
"Tank", and a spec name two classes share carries a number ("Protection1" is a paladin's, "Holy1" a paladin's,
"Restoration1" a shaman's). The class colour Raid-Helper sends with each slot settles which class it is.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from toads_api.comps.catalog import CLASSES, SPECS

SOURCE = "raid-helper"
# Far more than a raid: a bigger file is not a sign-up sheet.
MAX_ENTRIES = 200

# The WoW class colours Raid-Helper sends with each slot.
_COLOURS = {
    "#c69b6d": "warrior",
    "#f48cba": "paladin",
    "#aad372": "hunter",
    "#fff468": "rogue",
    "#ffffff": "priest",
    "#0070dd": "shaman",
    "#3fc7eb": "mage",
    "#8788ee": "warlock",
    "#ff7c0a": "druid",
}
# Raid-Helper's spec names, once their number is dropped, where they differ from ours.
_SPEC_NAMES = {"beastmastery": "beast-mastery"}
# Event sign-ups that are not a seat in the raid.
_NOT_ATTENDING = {"absence", "absent", "bench", "late", "tentative", "declined"}


@dataclass(frozen=True)
class Signup:
    """One person Raid-Helper seated, read as one of our specs."""

    discord_user_id: int
    name: str
    wow_class: str
    spec: str


@dataclass(frozen=True)
class Skipped:
    """A sign-up the import passes over, and why, in words an officer reads."""

    name: str
    reason: str
    discord_user_id: int | None = None


class ExportError(Exception):
    """Not a Raid-Helper export we can read."""


def _text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    return value.strip() if isinstance(value, str) else ""


def _user_id(raw: Mapping[str, Any]) -> int | None:
    value = raw.get("userId", raw.get("id"))
    text = str(value) if isinstance(value, int | str) else ""
    return int(text) if text.isdigit() and 0 < len(text) <= 19 else None


def _class_of(raw: Mapping[str, Any]) -> str | None:
    named = _text(raw, "className").lower()
    if named in CLASSES:
        return named
    # "Tank", or a class name we do not know: the colour says which class it is.
    return _COLOURS.get(_text(raw, "color").lower())


def _spec_of(wow_class: str, raw: Mapping[str, Any]) -> str | None:
    name = re.sub(r"\d+$", "", _text(raw, "specName")).strip().lower()
    key = _SPEC_NAMES.get(name, re.sub(r"[^a-z]+", "-", name).strip("-"))
    spec = f"{wow_class}-{key}"
    return spec if spec in SPECS else None


def _confirmed(raw: Mapping[str, Any]) -> bool:
    """A composition slot says `isConfirmed`; an event sign-up says `status` ("primary" for a seat)."""
    if "isConfirmed" in raw:
        value = raw["isConfirmed"]
        return value is True or (isinstance(value, str) and value.strip().lower() == "confirmed")
    status = _text(raw, "status").lower()
    return status in ("", "primary", "confirmed") and _text(raw, "className").lower() not in _NOT_ATTENDING


def _entries(export: object) -> list[Mapping[str, Any]]:
    if not isinstance(export, Mapping):
        raise ExportError("That is not a Raid-Helper export")
    raw = export.get("slots", export.get("signUps"))
    if not isinstance(raw, list):
        raise ExportError("That Raid-Helper export has no sign-ups in it")
    if len(raw) > MAX_ENTRIES:
        raise ExportError(f"That export has more than {MAX_ENTRIES} sign-ups")
    return [r for r in raw if isinstance(r, Mapping)]


def read_export(export: object) -> tuple[list[Signup], list[Skipped]]:
    """Each confirmed sign-up as a class and spec of ours, first sign-up per person, and the rest with a reason."""
    signups: list[Signup] = []
    skipped: list[Skipped] = []
    seen: set[int] = set()
    for raw in _entries(export):
        name = _text(raw, "name")[:100] or "Someone"
        user = _user_id(raw)
        if user is None:
            if name != "Someone" or raw.get("specName"):
                skipped.append(Skipped(name, "An open seat: no one in it"))
            continue
        if not _confirmed(raw):
            skipped.append(Skipped(name, "Not confirmed", user))
            continue
        if user in seen:
            skipped.append(Skipped(name, "Signed up twice; the first seat counts", user))
            continue
        wow_class = _class_of(raw)
        spec = _spec_of(wow_class, raw) if wow_class else None
        if wow_class is None or spec is None:
            label = " ".join(p for p in (_text(raw, "specName"), _text(raw, "className")) if p) or "nothing"
            skipped.append(Skipped(name, f"Unknown class or spec ({label[:60]})", user))
            continue
        seen.add(user)
        signups.append(Signup(user, name, wow_class, spec))
    return signups, skipped
