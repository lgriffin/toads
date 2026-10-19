"""The Logs page (docs/logs.md): every stored guild raid with the desktop app's raid analysis, published to the hub API.

Built with wcl-app's RaidPageService (guides/raid_pages.md in lgriffin/warcraftlogs_project) from wcl-store alone, so
it never calls Warcraft Logs. Every raid's page is built each run for the boss history; the list, the history and a hash
of each page go first, and the API answers with the raids whose analysis it does not hold in that build yet, which are
then sent one at a time. A raid that cannot be read back stays listed, so the hub keeps the analysis it already has.
`toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run `toads-worker publish-logs`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import structlog
from wcl_app import RaidPage, RaidPageService, RaidSummary
from wcl_app.context import StorageFactory
from wcl_app.raid_pages import RAID_PAGE_VERSION, boss_history

from toads_worker import hub_api, store
from toads_worker.settings import Settings

log = structlog.get_logger(__name__)

# The hub API's MAX_RAIDS: every stored guild raid.
MAX_RAIDS = 1000


@dataclass(frozen=True)
class Built:
    """Every stored guild raid, newest first, and the pages that could be read back."""

    summaries: list[RaidSummary]
    pages: list[RaidPage]


def page_hash(page: RaidPage) -> str:
    """The page's sha256, so the hub can tell a rebuilt analysis (an analyzer fix, a re-imported report) from the one
    it holds."""
    return hashlib.sha256(json.dumps(page.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_pages(storage: StorageFactory) -> Built:
    """Every stored guild raid and its page; a raid that cannot be read back is listed without one."""
    service = RaidPageService(storage)
    summaries = service.index(limit=MAX_RAIDS)
    pages = []
    for summary in summaries:
        page = service.page(summary.report_id, summary)
        if page is None:
            log.warning("logs.raid_unreadable", report=summary.report_id)
            continue
        pages.append(page)
    return Built(summaries, pages)


def build_index(built: Built, *, now: Callable[[], datetime] = datetime.now) -> dict[str, Any]:
    """The list, the boss history and each page's hash as JSON, for PUT /api/worker/logs."""
    return {
        "version": RAID_PAGE_VERSION,
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S"),
        "raids": [s.to_dict() for s in built.summaries],
        "bosses": [b.to_dict() for b in boss_history(built.pages)],
        "hashes": {p.summary.report_id: page_hash(p) for p in built.pages},
    }


@contextmanager
def _client(settings: Settings, hub: httpx.Client | None) -> Iterator[httpx.Client]:
    """The caller's client, or one for the whole run, closed after it."""
    if hub is not None:
        yield hub
        return
    with httpx.Client(base_url=settings.hub_api_url, timeout=30.0) as client:
        yield client


def _superseded(exc: httpx.HTTPStatusError) -> bool:
    """409: a newer run's list is already stored, so this run's work is out of date."""
    return exc.response.status_code == httpx.codes.CONFLICT


def publish_logs(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Send the list, then every analysis the API asks for. Returns how many raids it listed and sent."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    built = build_pages(storage or store.storage(settings))
    by_id = {p.summary.report_id: p for p in built.pages}
    sent = 0
    with _client(settings, hub) as client:
        try:
            answer = hub_api.put(settings, "/api/worker/logs", build_index(built), client)
        except httpx.HTTPStatusError as exc:
            if not _superseded(exc):
                raise
            log.info("logs.superseded")
            return {"raids": len(built.summaries), "sent": 0}
        for report_id in answer.get("missing", []):
            page = by_id.get(report_id)
            if page is None:
                continue
            try:
                hub_api.put(
                    settings, f"/api/worker/logs/{report_id}", {"page": page.to_dict(), "hash": page_hash(page)}, client
                )
            except httpx.HTTPStatusError as exc:
                if not _superseded(exc):
                    raise
                log.info("logs.page_superseded", report=report_id)
                continue
            sent += 1
    log.info("logs.published", raids=len(built.summaries), sent=sent)
    return {"raids": len(built.summaries), "sent": sent}
