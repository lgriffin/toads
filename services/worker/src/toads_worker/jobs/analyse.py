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
from wcl_core.auth import TokenManager
from wcl_core.client import WarcraftLogsClient

from toads_worker import store
from toads_worker.reports import parse_report_input
from toads_worker.settings import Settings

Progress = Callable[[str], None]


def build_client(settings: Settings) -> WarcraftLogsClient:
    """A WCL client using the worker's credentials, throttle and retry settings.

    The on-disk response cache is off: the worker runs in a read-only container, and raw responses
    will be cached in object storage instead (phase 2.1).
    """
    tokens = TokenManager(settings.wcl_client_id, settings.wcl_client_secret)
    client = WarcraftLogsClient(tokens, cache_enabled=False, api_url=settings.wcl_api_url)
    client.MIN_REQUEST_INTERVAL = settings.wcl_throttle_ms / 1000
    client.MAX_RETRIES = settings.wcl_max_retries
    return client


def analyse_report(
    value: str,
    *,
    settings: Settings | None = None,
    client: WarcraftLogsClient | None = None,
    storage: StorageFactory | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Validate a report code or URL, analyse and store it with wcl-app and return the analysis as a dict.

    The code is validated before any client is built, request made or database opened (REQ-CORE-SEC-002).
    """
    code = parse_report_input(value)
    if client is None or storage is None:
        settings = settings or Settings()
        client = build_client(settings) if client is None else client
        storage = store.storage(settings) if storage is None else storage
    ctx = AppContext.headless(client, storage=storage)
    analysis = RaidService(ctx).analyze_and_save(code, progress=progress)
    return dataclasses.asdict(analysis)
