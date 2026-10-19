"""The Logs page (docs/logs.md): every stored guild raid with the desktop app's raid analysis, published to the hub API.

Built with wcl-app's RaidPageService (guides/raid_pages.md in lgriffin/warcraftlogs_project) from wcl-store alone, so
it never calls Warcraft Logs. Every raid's page is built each run for the boss history; the list and the history go
first, and the API answers with the raids whose analysis it does not hold yet, which are then sent one at a time.
`toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run `toads-worker publish-logs`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import structlog
from wcl_app import RaidPage, RaidPageService
from wcl_app.context import StorageFactory
from wcl_app.raid_pages import RAID_PAGE_VERSION, boss_history

from toads_worker import hub_api, store
from toads_worker.settings import Settings

log = structlog.get_logger(__name__)

# The hub API's MAX_RAIDS: every stored guild raid.
MAX_RAIDS = 1000


def build_pages(storage: StorageFactory) -> list[RaidPage]:
    """Every stored guild raid's page, newest first; a raid that cannot be read back is left out."""
    service = RaidPageService(storage)
    pages = []
    for summary in service.index(limit=MAX_RAIDS):
        page = service.page(summary.report_id, summary)
        if page is None:
            log.warning("logs.raid_unreadable", report=summary.report_id)
            continue
        pages.append(page)
    return pages


def build_index(pages: list[RaidPage], *, now: Callable[[], datetime] = datetime.now) -> dict[str, Any]:
    """The list and the boss history as JSON, for PUT /api/worker/logs."""
    return {
        "version": RAID_PAGE_VERSION,
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S"),
        "raids": [p.summary.to_dict() for p in pages],
        "bosses": [b.to_dict() for b in boss_history(pages)],
    }


def publish_logs(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Send the list, then every analysis the API asks for. Returns how many raids it listed and sent."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    pages = build_pages(storage or store.storage(settings))
    answer = hub_api.put(settings, "/api/worker/logs", build_index(pages), hub)
    by_id = {p.summary.report_id: p for p in pages}
    sent = 0
    for report_id in answer.get("missing", []):
        page = by_id.get(report_id)
        if page is None:
            continue
        hub_api.put(settings, f"/api/worker/logs/{report_id}", {"page": page.to_dict()}, hub)
        sent += 1
    log.info("logs.published", raids=len(pages), sent=sent)
    return {"raids": len(pages), "sent": sent}
