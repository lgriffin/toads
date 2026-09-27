"""Finding the raid date a sheet tab describes, from its name or its first rows.

The guild is on an EU realm, so numeric dates are read day first (24/09/2026). ISO dates and written-out months
("24 Sep 2026", "Sept 24th 2026") are read too.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

_MONTHS = {
    name: i
    for i, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DMY = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b")
_D_MON_Y = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH})\.?,?\s+(\d{{4}})\b", re.IGNORECASE)
_MON_D_Y = re.compile(rf"\b({_MONTH})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.IGNORECASE)

# How far into a tab to look for a date when its name has none.
HEADER_ROWS = 5


def _make(year: int, month: int, day: int) -> date | None:
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def find_date(text: str) -> date | None:
    """The valid date that starts earliest in `text`, whatever its format, or None."""
    found: list[tuple[int, date]] = []
    for m in _ISO.finditer(text):
        if d := _make(int(m[1]), int(m[2]), int(m[3])):
            found.append((m.start(), d))
    for m in _DMY.finditer(text):
        if d := _make(int(m[3]), int(m[2]), int(m[1])):
            found.append((m.start(), d))
    for m in _D_MON_Y.finditer(text):
        if d := _make(int(m[3]), _MONTHS[m[2].lower()], int(m[1])):
            found.append((m.start(), d))
    for m in _MON_D_Y.finditer(text):
        if d := _make(int(m[3]), _MONTHS[m[1].lower()], int(m[2])):
            found.append((m.start(), d))
    return min(found, key=lambda f: f[0])[1] if found else None


def raid_date_of(tab: str, rows: Iterable[Iterable[str]]) -> date | None:
    """The tab name wins; otherwise the first date in the first few rows, read left to right."""
    if found := find_date(tab):
        return found
    for i, row in enumerate(rows):
        if i >= HEADER_ROWS:
            break
        for cell in row:
            if found := find_date(cell):
                return found
    return None


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def weekday_named(name: str) -> int | None:
    """0-6 when `name` mentions exactly one weekday ("Wednesday", "Sunday raid"), else None."""
    words = set(re.findall(r"[a-z]+", name.lower()))
    hits = [i for i, day in enumerate(_WEEKDAYS) if day in words or day[:3] in words]
    return hits[0] if len(hits) == 1 else None
