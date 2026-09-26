"""On-demand raid analysis through wcl-core, the same engine the desktop app runs.

Storing the result waits for wcl-store (analyzer phase 1.2); until then the job returns the analysis
as plain data so RQ keeps it as the job result.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from wcl_core.analysis import analyze_raid
from wcl_core.auth import TokenManager
from wcl_core.client import WarcraftLogsClient

from toads_worker.reports import parse_report_input
from toads_worker.settings import Settings

Progress = Callable[[str], None]


def build_client(settings: Settings) -> WarcraftLogsClient:
    """A WCL client using the worker's credentials, throttle and retry settings.

    The on-disk response cache is off: the worker runs in a read-only container, and raw responses
    will be cached in object storage instead (phase 2.1).
    """
    # wcl-core's TokenManager has no annotations yet (analyzer phase 1.1 adds them).
    tokens = TokenManager(settings.wcl_client_id, settings.wcl_client_secret.get_secret_value())  # type: ignore[no-untyped-call]
    client = WarcraftLogsClient(tokens, cache_enabled=False, api_url=settings.wcl_api_url)
    client.MIN_REQUEST_INTERVAL = settings.wcl_throttle_ms / 1000
    client.MAX_RETRIES = settings.wcl_max_retries
    return client


def analyse_report(
    value: str,
    *,
    settings: Settings | None = None,
    client: WarcraftLogsClient | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Validate a report code or URL, analyse it with wcl-core and return the analysis as a dict.

    The code is validated before any client is built or request made (REQ-CORE-SEC-002).
    """
    code = parse_report_input(value)
    if client is None:
        client = build_client(settings or Settings())
    analysis = analyze_raid(client, code, progress_callback=progress)
    return dataclasses.asdict(analysis)
