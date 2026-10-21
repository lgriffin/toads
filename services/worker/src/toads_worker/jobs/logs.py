"""The Logs page (docs/logs.md): every stored guild raid with the desktop app's raid analysis, published to the hub API.

Built with wcl-app's RaidPageService (guides/raid_pages.md in lgriffin/warcraftlogs_project) from wcl-store alone, so
it never calls Warcraft Logs. Every raid's page is built each run for the boss history; the list, the history and a hash
of each page go first, and the API answers with the raids whose analysis it does not hold in that build yet, which are
then sent one at a time. A raid that cannot be read back stays listed, so the hub keeps the analysis it already has.
One raid the hub refuses never holds back the others: the run sends every other analysis, then fails naming it.
`toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run `toads-worker publish-logs`.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
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
# Uploads the hub failed to answer in a row (timeouts, refused connections) before the run gives up on the rest, so a
# stalled hub costs the scheduler a few request timeouts rather than one per raid it asked for.
MAX_UNANSWERED = 3


@dataclass(frozen=True)
class Built:
    """Every stored guild raid, newest first, and the pages that could be read back."""

    summaries: list[RaidSummary]
    pages: list[RaidPage]


def plain(value: Any) -> Any:
    """`value` as strict JSON can carry it: a NaN or infinite number (an empty fight's ratio) becomes null, since the
    hub's client refuses to encode one at all."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def page_body(page: RaidPage) -> dict[str, Any]:
    """The page as the hub receives it."""
    body: dict[str, Any] = plain(page.to_dict())
    return body


def page_hash(page: RaidPage) -> str:
    """The page's sha256, so the hub can tell a rebuilt analysis (an analyzer fix, a re-imported report) from the one
    it holds."""
    return hashlib.sha256(json.dumps(page_body(page), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
        "raids": [plain(s.to_dict()) for s in built.summaries],
        "bosses": [plain(b.to_dict()) for b in boss_history(built.pages)],
        "hashes": {p.summary.report_id: page_hash(p) for p in built.pages},
    }


def _superseded(exc: httpx.HTTPStatusError) -> bool:
    """409: a newer run's list is already stored, so this run's work is out of date."""
    return exc.response.status_code == httpx.codes.CONFLICT


def publish_logs(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Send the list, then every analysis the API asks for. Returns how many raids it listed, sent and could not read
    back; raises after the last one when the hub refused any, so the scheduler logs the run as failed."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    built = build_pages(storage or store.storage(settings))
    by_id = {p.summary.report_id: p for p in built.pages}
    # Raids listed without an analysis to send: their pages say "not analysed" until the analyzer can read them back.
    unreadable = len(built.summaries) - len(built.pages)
    with hub_api.client(settings, hub) as client:
        try:
            answer = hub_api.put(settings, "/api/worker/logs", build_index(built), client)
        except httpx.HTTPStatusError as exc:
            if not _superseded(exc):
                raise
            log.info("logs.superseded")
            return {"raids": len(built.summaries), "sent": 0, "unreadable": unreadable}
        sent, failed, left = _send_pages(settings, client, answer.get("missing", []), by_id)
    log.info(
        "logs.published", raids=len(built.summaries), sent=sent, failed=len(failed), left=left, unreadable=unreadable
    )
    if failed:
        message = f"The hub did not take the analysis of {len(failed)} raid(s): {', '.join(failed)}"
        if left:
            message += f"; it stopped answering, so {left} more wait for the next run"
        raise RuntimeError(message)
    return {"raids": len(built.summaries), "sent": sent, "unreadable": unreadable}


def _send_pages(
    settings: Settings, client: httpx.Client, missing: list[str], by_id: dict[str, RaidPage]
) -> tuple[int, list[str], int]:
    """Send each analysis the hub asked for. Returns how many it took, the raids it refused or never answered for, and
    how many were left unsent after MAX_UNANSWERED unanswered uploads in a row."""
    sent, unanswered = 0, 0
    failed: list[str] = []
    wanted = [r for r in missing if r in by_id]
    for i, report_id in enumerate(wanted):
        if unanswered >= MAX_UNANSWERED:
            return sent, failed, len(wanted) - i
        page = by_id[report_id]
        try:
            body = {"page": page_body(page), "hash": page_hash(page)}
            hub_api.put(settings, f"/api/worker/logs/{report_id}", body, client)
        except httpx.HTTPStatusError as exc:
            unanswered = 0
            if _superseded(exc):
                log.info("logs.page_superseded", report=report_id)
                continue
            log.error("logs.page_refused", report=report_id, status=exc.response.status_code, detail=_detail(exc))
            failed.append(report_id)
            continue
        except httpx.TransportError as exc:  # a timeout or a dropped connection: the next raid still goes
            unanswered += 1
            log.error("logs.page_failed", report=report_id, error=repr(exc))
            failed.append(report_id)
            continue
        except ValueError as exc:  # a page strict JSON cannot carry
            log.error("logs.page_failed", report=report_id, error=repr(exc))
            failed.append(report_id)
            continue
        unanswered = 0
        sent += 1
    return sent, failed, 0


def _detail(exc: httpx.HTTPStatusError) -> str:
    """The API's reason, cut short for the log."""
    return exc.response.text[:300]
