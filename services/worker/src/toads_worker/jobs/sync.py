"""Guild-report sync (REQ-DEV-OPS-004): analyse and store the guild's Warcraft Logs reports that wcl-store does not
have yet, through the analyzer's RaidService, on the guild key.

`toads-worker schedule` runs it every TOADS_SYNC_REFRESH_MINUTES, before the publish jobs, so new raids reach the hub
home, /me and the reference lists on the same turn. Run it by hand with `toads-worker sync`, or analyse one report with
`toads-worker analyse <code or URL>`.

How much one run imports comes from the guild key's Warcraft Logs rate limit (REQ-DEV-OPS-005): before each report the
run reads the points spent this hour, and it stops once the next report would eat into the TOADS_SYNC_RESERVE_PERCENT
of the hour's points kept back for everything else on the key. A report's cost is not known up front, so the run
assumes the next one costs as much as the dearest it has imported so far. A run also stops when the hour's points
reset, so the publish jobs get their turn; the next run picks up the new hour's points. TOADS_SYNC_BATCH, when set,
caps the reports per run on top of that, and is the cap when Warcraft Logs does not report the rate limit.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

import structlog
from wcl_app import AppContext, RaidService
from wcl_core.client import WarcraftLogsClient

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


# The cap per run when Warcraft Logs does not say how many points are left and TOADS_SYNC_BATCH is not set.
FALLBACK_BATCH = 10

RATE_LIMIT_QUERY = "query { rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn } }"


@dataclass(frozen=True)
class RateLimit:
    """The key's Warcraft Logs rate limit as the API reports it."""

    limit_per_hour: float
    spent_this_hour: float
    reset_in_seconds: float

    def allowance(self, reserve_percent: int) -> float:
        """Points still free this hour once the reserve is kept back."""
        return self.limit_per_hour * (100 - reserve_percent) / 100 - self.spent_this_hour


class Budget(Protocol):
    """Reads the key's rate limit; None when Warcraft Logs does not answer."""

    def read(self) -> RateLimit | None: ...


class WclBudget:
    """The rate limit of the key behind `client`, from the API's rateLimitData."""

    def __init__(self, client: WarcraftLogsClient) -> None:
        self._client = client

    def read(self) -> RateLimit | None:
        try:
            data = self._client.run_query(RATE_LIMIT_QUERY, use_cache=False)["data"]["rateLimitData"]
            return RateLimit(
                float(data["limitPerHour"]), float(data["pointsSpentThisHour"]), float(data["pointsResetIn"])
            )
        except Exception:  # an unreadable rate limit falls back to the fixed batch; it never fails the sync
            log.warning("sync.rate_limit_unreadable")
            return None


def _rate_limited(exc: Exception) -> bool:
    """Warcraft Logs answered 429 even after the client's retries."""
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 429


def raid_service(settings: Settings, client: WarcraftLogsClient | None = None) -> RaidService:
    """The analyzer's raid service on the guild key and the hub database."""
    client = client or client_for(settings, None)
    return RaidService(AppContext.headless(client, storage=store.storage(settings)))


def sync_guild_reports(
    settings: Settings,
    *,
    raids: Raids | None = None,
    budget: Budget | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Import the guild's reports not stored yet, newest first, while the guild key's rate limit allows.

    A report that fails to analyse is logged and listed under `failed`, and the next older report takes its place, so a
    log that never analyses cannot hold back the rest of the history; failed reports are tried again next run. With a
    fixed batch, a run stops after twice the batch in attempts. `remaining` counts the new reports still not stored,
    failed ones included, and `stopped` says why the run ended.
    """
    if settings.wcl_guild_id <= 0:
        raise ValueError("Set TOADS_WCL_GUILD_ID to the guild's Warcraft Logs id before syncing")
    if raids is None or budget is None:
        client = client_for(settings, None)
        raids = raids or raid_service(settings, client)
        budget = budget or WclBudget(client)
    # Warcraft Logs lists a guild's reports newest first, so the newest raids reach the hub first (FullHistory, for the
    # backfill, lists them oldest first).
    remote = [r["code"] for r in raids.guild_reports(settings.wcl_guild_id)]
    new = new_report_codes(remote, raids.imported_codes())
    run = _Run(settings, budget)
    for code in new:
        if run.should_stop():
            break
        try:
            raids.analyze_and_save(code, progress=progress)
        except Exception as exc:  # one broken report must not stop the rest; it is retried next run
            if _rate_limited(exc):
                log.warning("sync.rate_limited", report=code)
                run.stopped = "rate_limited"
                break
            log.exception("sync.report_failed", report=code)
            run.failed[code] = str(exc) or type(exc).__name__
        else:
            run.imported.append(code)
        run.spent()
    else:
        run.stopped = "done"  # every new report was tried, whatever the last rate-limit reading said
    remaining = len(new) - len(run.imported)
    log.info(
        "sync.done",
        imported=len(run.imported),
        failed=len(run.failed),
        remaining=remaining,
        stopped=run.stopped,
        points_left=run.points_left(),
    )
    return {
        "imported": run.imported,
        "failed": run.failed,
        "remaining": remaining,
        "stopped": run.stopped,
        "points_left": run.points_left(),
    }


class _Run:
    """One sync run's progress and the rule for when it stops."""

    def __init__(self, settings: Settings, budget: Budget) -> None:
        self.imported: list[str] = []
        self.failed: dict[str, str] = {}
        self.stopped = ""
        self._reserve = settings.sync_reserve_percent
        self._budget = budget
        self._reading = budget.read()
        self._cap = settings.sync_batch or (None if self._reading else FALLBACK_BATCH)
        # The dearest report so far, in points: the guess for what the next one costs.
        self._dearest = 0.0

    def should_stop(self) -> bool:
        if not self.stopped:
            if self._cap is not None and (len(self.imported) >= self._cap or self._attempts() >= self._cap * 2):
                self.stopped = "batch"
            elif self._reading is not None and self._reading.allowance(self._reserve) <= self._dearest:
                self.stopped = "rate_limit_budget"
        return bool(self.stopped)

    def spent(self) -> None:
        """Read the rate limit again after a report, and learn what that report cost."""
        if self._reading is None:
            return
        after = self._budget.read()
        if after is None:
            # Without numbers the run cannot tell how close it is to the limit; stop rather than guess.
            self.stopped = "rate_limit_unknown"
        elif after.spent_this_hour < self._reading.spent_this_hour:
            # The hour's points reset mid-run: let the publish jobs run; the next run spends the new hour's points.
            self.stopped = "rate_limit_reset"
        else:
            self._dearest = max(self._dearest, after.spent_this_hour - self._reading.spent_this_hour)
        self._reading = after

    def points_left(self) -> float | None:
        return None if self._reading is None else round(self._reading.allowance(self._reserve), 1)

    def _attempts(self) -> int:
        return len(self.imported) + len(self.failed)


# More reports than any guild has: the backfill lists the guild's whole history, not the newest 350.
ALL_REPORTS = 100_000
# How long the backfill waits when Warcraft Logs does not say when the hour's points reset.
UNKNOWN_RESET_WAIT_SECONDS = 300.0


class FullHistory:
    """The analyzer's raids, listing every guild report on Warcraft Logs oldest first.

    Oldest first, so the backfill works from the far end of the history while the scheduler's sync takes the newest
    reports: the two meet once rather than racing each other for the same reports.
    """

    def __init__(self, service: Raids, client: WarcraftLogsClient) -> None:
        self._service = service
        self._client = client

    def guild_reports(self, guild_id: int) -> list[dict[str, Any]]:
        return list(reversed(self._client.get_guild_reports(guild_id, total=ALL_REPORTS)))

    def imported_codes(self) -> set[str]:
        return self._service.imported_codes()

    def analyze_and_save(self, report_id: str, *, progress: Progress | None = None) -> object:
        return self._service.analyze_and_save(report_id, progress=progress)


def backfill_guild_reports(
    settings: Settings,
    *,
    raids: Raids | None = None,
    budget: Budget | None = None,
    progress: Progress | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Import every guild report on Warcraft Logs not stored yet (REQ-DEV-OPS-006), oldest first.

    It runs the sync again and again, on the same rate-limit budget, and when the hour's points are spent it waits for
    them to reset. It ends once a run imports nothing new: everything is stored, or only reports that never analyse
    (empty or trash-only logs) are left, listed under `failed`.
    """
    if raids is None or budget is None:
        client = client_for(settings, None)
        raids = raids or FullHistory(raid_service(settings, client), client)
        budget = budget or WclBudget(client)
    imported: list[str] = []
    failed: dict[str, str] = {}
    while True:
        result = sync_guild_reports(settings, raids=raids, budget=budget, progress=progress)
        imported += result["imported"]
        failed = {**{c: e for c, e in failed.items() if c not in result["imported"]}, **result["failed"]}
        # "done" means the run tried every report left, so whatever remains failed to analyse.
        if result["stopped"] == "done" or not result["remaining"]:
            break
        if result["stopped"] in {"rate_limit_budget", "rate_limited", "rate_limit_unknown"}:
            reading = budget.read()
            wait = reading.reset_in_seconds + 5 if reading else UNKNOWN_RESET_WAIT_SECONDS
            log.info("backfill.waiting", seconds=wait, imported=len(imported), remaining=result["remaining"])
            if progress:
                progress(f"Waiting {wait / 60:.0f} min for the Warcraft Logs points to reset")
            sleep(wait)
    log.info("backfill.done", imported=len(imported), failed=len(failed))
    return {"imported": len(imported), "failed": failed, "remaining": result["remaining"]}
