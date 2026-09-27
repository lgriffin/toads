"""On-demand raid analysis through the analyzer's services layer (wcl-app), the same use case the desktop
app runs: saved role overrides and thresholds apply, and the result is stored in wcl-store's Postgres tables.

The job also returns the analysis as plain data so RQ keeps it as the job result.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from wcl_app import AppContext, RaidService
from wcl_app.context import StorageFactory
from wcl_core.client import WarcraftLogsClient

from toads_worker import store
from toads_worker.reports import parse_report_input
from toads_worker.settings import Settings
from toads_worker.wcl_keys import client_for

Progress = Callable[[str], None]


def build_client(settings: Settings, member_id: int | None = None) -> WarcraftLogsClient:
    """A WCL client with the worker's throttle and retry settings, on the member's own key when they saved one
    (see `toads_worker.wcl_keys`), else on the guild key."""
    return client_for(settings, member_id)


def analyse_report(
    value: str,
    *,
    settings: Settings | None = None,
    client: WarcraftLogsClient | None = None,
    storage: StorageFactory | None = None,
    progress: Progress | None = None,
    member_id: int | None = None,
) -> dict[str, Any]:
    """Validate a report code or URL, analyse and store it with wcl-app and return the analysis as a dict.

    `member_id` is the member the analysis is for, when there is one: their own Warcraft Logs key is used if saved.

    The code is validated before any client is built, request made or database opened (REQ-CORE-SEC-002).
    """
    code = parse_report_input(value)
    if client is None or storage is None:
        settings = settings or Settings()
        client = build_client(settings, member_id) if client is None else client
        storage = store.storage(settings) if storage is None else storage
    ctx = AppContext.headless(client, storage=storage)
    analysis = RaidService(ctx).analyze_and_save(code, progress=progress)
    return dataclasses.asdict(analysis)
