"""On-demand raid analysis through wcl-core, the same engine the desktop app runs.

Storing the result waits for wcl-store (analyzer phase 1.2); until then the job returns the analysis
as plain data so RQ keeps it as the job result.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from wcl_core.analysis import analyze_raid
from wcl_core.client import WarcraftLogsClient

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
    progress: Progress | None = None,
    member_id: int | None = None,
) -> dict[str, Any]:
    """Validate a report code or URL, analyse it with wcl-core and return the analysis as a dict.

    `member_id` is the member the analysis is for, when there is one: their own Warcraft Logs key is used if saved.

    The code is validated before any client is built or request made (REQ-CORE-SEC-002).
    """
    code = parse_report_input(value)
    if client is None:
        client = build_client(settings or Settings(), member_id)
    # TODO(wcl-app): call RaidService.analyze once the analyzer's services layer is packaged, so role overrides
    # and thresholds match the desktop app. Until then keep this job a thin call; add no analysis logic here.
    analysis = analyze_raid(client, code, progress_callback=progress)
    return dataclasses.asdict(analysis)
