"""What the hub keeps from a downloaded spreadsheet: which tabs, which cells, and the report it was run for.

The CBA (Combat Log Analytics) and RPB (Role Performance Breakdown) sheets are run by pasting a Warcraft Logs report
into an Instructions tab, next to the runner's Discord webhook, e-mail and API key. Those setup tabs are never stored,
and any webhook or e-mail that shows up elsewhere is blanked, because every member can read a stored tab.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from fnmatch import fnmatch

# Setup and lookup tabs of the CLA and RPB templates: instructions, translations and item configs.
SETUP_TABS = ("instructions", "trans", "*config*", "settings", "all", "start")

REDACTED = "[redacted]"
_SECRETS = re.compile(
    r"https?://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+"  # anyone holding it can post to the channel
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+",  # e-mail addresses
    re.IGNORECASE,
)
_REPORT = re.compile(r"warcraftlogs\.com/reports/([A-Za-z0-9]{16})\b")


def keeps(tab: str, patterns: Sequence[str] | None) -> bool:
    """With `patterns` (a source's `tabs`), only matching tabs are kept; without, every tab but the setup ones."""
    name = tab.strip().lower()
    if patterns is not None:
        return any(fnmatch(name, p.lower()) for p in patterns)
    return not any(fnmatch(name, p) for p in SETUP_TABS)


def redact(cell: str) -> str:
    return _SECRETS.sub(REDACTED, cell)


def report_code(cells: Iterable[str]) -> str | None:
    """The Warcraft Logs report the sheet was run for, from the report URL on its Instructions tab."""
    for cell in cells:
        if m := _REPORT.search(cell):
            return m[1]
    return None
