"""Rules for reference comparison. No RBAC, web framework, HTTP or storage imports: the routes decide who may call
these (officers, scoped to their raid day), the repository decides where state lives, and `enqueue` hands a job to
the worker, which does the Warcraft Logs work with wcl-app's ReferenceService (lgriffin/warcraftlogs_project,
guides/reference_comparison.md). The worker checks everything again against the stored raids; these checks only
refuse what can never work, so an officer hears about it at once.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from toads_api.reference.repository import (
    ComparisonSummary,
    Job,
    LoginInfo,
    ReferenceRepository,
    StoredComparison,
    StoredPage,
    UserToken,
)

_CODE = re.compile(r"[A-Za-z0-9]{16}")
_URL = re.compile(r"warcraftlogs\.com/reports/([A-Za-z0-9]{16})(?![A-Za-z0-9])")
MAX_LABEL_LENGTH = 80
MAX_REPORT_INPUT = 300
RECENT_JOBS = 10


class ReferenceRequestError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class QueueUnavailable(Exception):
    """The job queue could not take the job; nothing will run it."""


def parse_report(text: str) -> str:
    """A report code from a bare 16-character code or a Warcraft Logs report URL."""
    text = (text or "").strip()
    if len(text) > MAX_REPORT_INPUT:
        raise ReferenceRequestError("That is not a Warcraft Logs report code or link.")
    if _CODE.fullmatch(text):
        return text
    match = _URL.search(text)
    if match is None:
        raise ReferenceRequestError("That is not a Warcraft Logs report code or link.")
    return match.group(1)


def clean_label(label: str | None) -> str | None:
    label = " ".join((label or "").split())
    if len(label) > MAX_LABEL_LENGTH:
        raise ReferenceRequestError(f"A label is at most {MAX_LABEL_LENGTH} characters.")
    return label or None


@dataclass(frozen=True)
class Overview:
    configured: bool
    login: LoginInfo
    page: StoredPage | None
    comparisons: list[ComparisonSummary]
    jobs: list[Job]


class ReferenceService:
    def __init__(self, repo: ReferenceRepository, enqueue: Callable[[str], None], *, configured: bool) -> None:
        self.repo = repo
        # Hands a job id to the worker (toads_worker.jobs.reference.run_reference_job).
        self.enqueue = enqueue
        # Whether the hub has a Warcraft Logs application to sign in with.
        self.configured = configured

    def overview(self) -> Overview:
        return Overview(
            configured=self.configured,
            login=self.repo.login_info(),
            page=self.repo.page(),
            comparisons=self.repo.comparisons(),
            jobs=self.repo.recent_jobs(RECENT_JOBS),
        )

    # ── The dedicated login ──

    def require_configured(self) -> None:
        if not self.configured:
            raise ReferenceRequestError("The hub has no Warcraft Logs application configured.", 503)

    def connect(self, token: UserToken, member_id: int) -> None:
        self.repo.save_login(token, member_id)

    def disconnect(self) -> bool:
        return self.repo.delete_login()

    # ── Requests the worker carries out ──

    def request_import(self, raid_day: str, member_id: int, report: str, label: str | None) -> Job:
        code, label = parse_report(report), clean_label(label)
        login = self.repo.login_info()
        if not login.connected:
            raise ReferenceRequestError("Connect the Warcraft Logs account before importing a reference.", 409)
        if login.status == "expired":
            raise ReferenceRequestError("The Warcraft Logs sign-in has expired; connect the account again.", 409)
        return self._queue("import", raid_day, member_id, {"report": code, "label": label})

    def request_compare(self, raid_day: str, member_id: int, guild_report: str, reference_report: str) -> Job:
        guild, ref = parse_report(guild_report), parse_report(reference_report)
        if guild == ref:
            raise ReferenceRequestError("Pick one of our raids and a different reference raid.")
        return self._queue("compare", raid_day, member_id, {"guild_report": guild, "reference_report": ref})

    def request_label(self, raid_day: str, member_id: int, report: str, label: str | None) -> Job:
        return self._queue("label", raid_day, member_id, {"report": parse_report(report), "label": clean_label(label)})

    def request_delete(self, raid_day: str, member_id: int, report: str) -> Job:
        return self._queue("delete", raid_day, member_id, {"report": parse_report(report)})

    def comparison(self, guild_report: str, reference_report: str) -> StoredComparison | None:
        return self.repo.comparison(parse_report(guild_report), parse_report(reference_report))

    def _queue(self, kind: str, raid_day: str, member_id: int, params: dict[str, str | None]) -> Job:
        job = self.repo.create_job(kind, raid_day, member_id, dict(params))
        try:
            self.enqueue(job.id)
        except QueueUnavailable:
            self.repo.fail_job(job.id, "The worker queue is unavailable; try again shortly.")
            raise ReferenceRequestError("The worker queue is unavailable; try again shortly.", 503) from None
        return job
