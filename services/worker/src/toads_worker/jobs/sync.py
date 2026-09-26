"""Nightly guild-report sync. Fetching and analysis plug in once wcl-core is published."""

from __future__ import annotations

from collections.abc import Iterable


def new_report_codes(remote: Iterable[str], known: Iterable[str]) -> list[str]:
    """Codes present on Warcraft Logs but not yet in raids.report_id, oldest first, de-duplicated."""
    seen = set(known)
    out: list[str] = []
    for code in remote:
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out
