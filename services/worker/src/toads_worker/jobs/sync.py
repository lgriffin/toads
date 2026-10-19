"""Guild-report sync (REQ-DEV-OPS-004): analyse and store the guild's Warcraft Logs reports that wcl-store does not
have yet, through the analyzer's RaidService, on the guild key.

`toads-worker schedule` runs it every TOADS_SYNC_REFRESH_MINUTES, before the publish jobs, so new raids reach the hub
home, /me and the reference lists on the same turn. Run it by hand with `toads-worker sync`, or analyse one report with
`toads-worker analyse <code or URL>`. Each run imports at most TOADS_SYNC_BATCH reports, newest first, so a first run
on a guild with a long history fills in over several turns instead of holding the Warcraft Logs quota for hours.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol

import structlog
from wcl_app import AppContext, RaidService

from toads_worker import store
from toads_worker.settings import Settings
from toads_worker.wcl_keys import client_for

log = structlog.get_logger(__name__)

Progress = Callable[[str], None]


class Raids(Protocol):
    """The part of wcl_app.RaidService the sync uses."""

    def guild_reports(self, guild_id: int) -> list[dict[str, Any]]: ...

    def imported_codes(self) -> set[str]: ...

    def analyze_and_save(self, report_id: str, *, progress: Progress | None = None) -> object: ...


def new_report_codes(remote: Iterable[str], known: Iterable[str]) -> list[str]:
    """Codes present on Warcraft Logs but not yet in raids.report_id, in the order given, de-duplicated."""
    seen = set(known)
    out: list[str] = []
    for code in remote:
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


def raid_service(settings: Settings) -> RaidService:
    """The analyzer's raid service on the guild key and the hub database."""
    return RaidService(AppContext.headless(client_for(settings, None), storage=store.storage(settings)))


def sync_guild_reports(
    settings: Settings, *, raids: Raids | None = None, progress: Progress | None = None
) -> dict[str, Any]:
    """Import up to TOADS_SYNC_BATCH of the guild's reports not stored yet, newest first.

    A report that fails to analyse is logged and listed under `failed`, and the next older report takes its place, so a
    log that never analyses cannot hold back the rest of the history. A run stops after twice the batch in attempts,
    to bound the Warcraft Logs calls one run spends on failures; failed reports are tried again next run. `remaining`
    counts the new reports still not stored, failed ones included.
    """
    if settings.wcl_guild_id <= 0:
        raise ValueError("Set TOADS_WCL_GUILD_ID to the guild's Warcraft Logs id before syncing")
    raids = raids or raid_service(settings)
    # Warcraft Logs lists a guild's reports newest first, so the newest raids reach the hub first.
    remote = [r["code"] for r in raids.guild_reports(settings.wcl_guild_id)]
    new = new_report_codes(remote, raids.imported_codes())
    imported: list[str] = []
    failed: dict[str, str] = {}
    for code in new[: settings.sync_batch * 2]:
        if len(imported) == settings.sync_batch:
            break
        try:
            raids.analyze_and_save(code, progress=progress)
        except Exception as exc:  # one broken report must not stop the rest; it is retried next run
            log.exception("sync.report_failed", report=code)
            failed[code] = str(exc) or type(exc).__name__
        else:
            imported.append(code)
    remaining = len(new) - len(imported)
    log.info("sync.done", imported=len(imported), failed=len(failed), remaining=remaining)
    return {"imported": imported, "failed": failed, "remaining": remaining}
