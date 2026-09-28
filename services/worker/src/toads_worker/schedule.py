"""`toads-worker schedule`: keeps the hub's derived pages fresh without cron (REQ-DEV-OPS-003).

Runs in its own container (infra/docker-compose.yml, service `scheduler`) on the worker image. Every job runs once at
start, then again each interval. A job that fails is logged and tried again at its next turn; it never stops the
others. Intervals come from the environment, and 0 turns a job off:

- publish-home, publish-performance and publish-reference: every TOADS_HUB_REFRESH_MINUTES (default 30)
- import-sheets: every TOADS_SHEETS_REFRESH_MINUTES (default 360), only when the raid sheets config exists
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import structlog

from toads_worker.jobs.home import publish_home_page
from toads_worker.jobs.performance import publish_performance
from toads_worker.jobs.reference import publish_reference_page
from toads_worker.jobs.sheets import import_raid_sheets
from toads_worker.settings import Settings

log = structlog.get_logger(__name__)

# The longest the loop sleeps, so a clock change or a paused container is noticed within a minute.
MAX_SLEEP_SECONDS = 60.0


@dataclass
class Job:
    name: str
    every_seconds: float
    run: Callable[[], object]
    # Monotonic time of the next run; 0 runs it at once.
    next_at: float = 0.0


def jobs_for(settings: Settings) -> list[Job]:
    """The jobs this environment turns on, in the order they run when due together."""
    jobs: list[Job] = []
    if settings.hub_refresh_minutes:
        every = settings.hub_refresh_minutes * 60.0
        jobs.append(Job("publish-home", every, lambda: publish_home_page(settings)))
        jobs.append(Job("publish-performance", every, lambda: publish_performance(settings)))
        # The raids officers pick from on the reference comparison page, so newly synced raids show up there.
        jobs.append(Job("publish-reference", every, lambda: publish_reference_page(settings)))
    if settings.sheets_refresh_minutes and settings.raid_sheets_config.is_file():
        jobs.append(Job("import-sheets", settings.sheets_refresh_minutes * 60.0, lambda: import_raid_sheets(settings)))
    return jobs


def run_due(jobs: list[Job], now: float) -> list[str]:
    """Run every job whose time has come and book its next run. Returns the names of the jobs that ran."""
    ran: list[str] = []
    for job in jobs:
        if job.next_at > now:
            continue
        ran.append(job.name)
        job.next_at = now + job.every_seconds
        try:
            job.run()
        except Exception:  # a failed run must not stop the loop or the other jobs; it runs again next turn
            log.exception("schedule.job_failed", job=job.name)
        else:
            log.info("schedule.job_done", job=job.name)
    return ran


def run_forever(
    jobs: list[Job],
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    keep_going: Callable[[], bool] = lambda: True,
) -> None:
    """Run the jobs on their intervals until `keep_going` answers False (tests only; the container runs forever)."""
    if not jobs:
        raise RuntimeError("Every scheduled job is turned off; set TOADS_HUB_REFRESH_MINUTES or remove the scheduler")
    log.info("schedule.started", jobs={j.name: j.every_seconds for j in jobs})
    while keep_going():
        run_due(jobs, clock())
        wait = min(j.next_at for j in jobs) - clock()
        sleep(min(max(wait, 1.0), MAX_SLEEP_SECONDS))
