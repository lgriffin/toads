"""Rules for reference comparison. No RBAC, web framework, HTTP or storage imports: the routes decide who may call
these (officers, scoped to their raid day), the repository decides where state lives, and `enqueue` hands a job to
the worker, which does the Warcraft Logs work with wcl-app's ReferenceService (lgriffin/warcraftlogs_project,
guides/reference_comparison.md). The worker checks everything again against the stored raids; these checks only
refuse what can never work, so an officer hears about it at once.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

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
# How many of the newest requests a night's overview looks through for its own (the hub keeps 100).
JOBS_SCANNED = 100


def pair_key(guild_report: str, reference_report: str) -> str:
    """The key a comparison's owning nights are kept under."""
    return f"{guild_report}/{reference_report}"


def _seen(owners: frozenset[str] | None, nights: frozenset[str] | None) -> bool:
    """Whether officers of `nights` (None: the global tier) see something these nights own (None: shared)."""
    return nights is None or owners is None or bool(owners & nights)


# A job still queued or running this long after its last update was lost (the worker died or RQ's 30-minute
# timeout killed it before it could record an outcome); the page shows it failed instead of polling forever.
ABANDONED_AFTER = timedelta(hours=1)
ABANDONED_MESSAGE = "The worker did not finish this request; try again."


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
    def __init__(
        self,
        repo: ReferenceRepository,
        enqueue: Callable[[str], None],
        *,
        configured: bool,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repo = repo
        self.clock = clock
        # Hands a job id to the worker (toads_worker.jobs.reference.run_reference_job).
        self.enqueue = enqueue
        # Whether the hub has a Warcraft Logs application to sign in with.
        self.configured = configured

    def overview(self, nights: frozenset[str] | None = None) -> Overview:
        """What the reference page shows. With `nights` (a night officer's), only those nights' references,
        comparisons and requests, and the shared ones from before nights were kept apart; None: everything."""
        page = self.repo.page()
        owners = self.repo.owners()
        if nights is not None and page is not None:
            page = replace(
                page,
                references=[r for r in page.references if _seen(owners.get(str(r.get("report_id", ""))), nights)],
            )
        jobs = self.repo.recent_jobs(RECENT_JOBS if nights is None else JOBS_SCANNED)
        return Overview(
            configured=self.configured,
            login=self.repo.login_info(),
            page=page,
            comparisons=[
                c
                for c in self.repo.comparisons()
                if _seen(owners.get(pair_key(c.guild_report, c.reference_report)), nights)
            ],
            jobs=[self._settled(j) for j in jobs if nights is None or j.raid_day in nights][:RECENT_JOBS],
        )

    def _settled(self, job: Job) -> Job:
        if job.status not in ("queued", "running"):
            return job
        updated = job.updated_at if job.updated_at.tzinfo else job.updated_at.replace(tzinfo=UTC)
        if self.clock() - updated < ABANDONED_AFTER:
            return job
        return replace(job, status="failed", message=ABANDONED_MESSAGE)

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
        job = self._queue("import", raid_day, member_id, {"report": code, "label": label})
        self.repo.own(code, raid_day)
        return job

    def request_compare(self, raid_day: str, member_id: int, guild_report: str, reference_report: str) -> Job:
        guild, ref = parse_report(guild_report), parse_report(reference_report)
        if guild == ref:
            raise ReferenceRequestError("Pick one of our raids and a different reference raid.")
        job = self._queue("compare", raid_day, member_id, {"guild_report": guild, "reference_report": ref})
        self.repo.own(pair_key(guild, ref), raid_day)
        return job

    def request_label(
        self, raid_day: str, member_id: int, report: str, label: str | None, nights: frozenset[str] | None = None
    ) -> Job:
        code = parse_report(report)
        self._check_changeable(code, nights)
        return self._queue("label", raid_day, member_id, {"report": code, "label": clean_label(label)})

    def request_delete(self, raid_day: str, member_id: int, report: str, nights: frozenset[str] | None = None) -> Job:
        code = parse_report(report)
        self._check_changeable(code, nights)
        return self._queue("delete", raid_day, member_id, {"report": code})

    def _check_changeable(self, report: str, nights: frozenset[str] | None) -> None:
        """A night's officers (`nights`) relabel or delete only a reference their nights imported and no other night
        did; a shared one, or one another night also uses, is left to a global officer. None: the global tier."""
        if nights is None:
            return
        owners = self.repo.owners().get(report)
        if owners is not None and not owners & nights:
            raise ReferenceRequestError("No such reference raid for this night.", 404)
        if owners is None:
            raise ReferenceRequestError(
                "This reference is shared with every night; a global officer can change it.", 403
            )
        if not owners <= nights:
            raise ReferenceRequestError("Another night uses this reference too; a global officer can change it.", 409)

    def comparison(
        self, guild_report: str, reference_report: str, nights: frozenset[str] | None = None
    ) -> StoredComparison | None:
        """A built comparison, or None when there is none, or it is another night's (`nights`: a night officer's)."""
        guild, ref = parse_report(guild_report), parse_report(reference_report)
        if not _seen(self.repo.owners().get(pair_key(guild, ref)), nights):
            return None
        return self.repo.comparison(guild, ref)

    def _queue(self, kind: str, raid_day: str, member_id: int, params: dict[str, str | None]) -> Job:
        job = self.repo.create_job(kind, raid_day, member_id, dict(params))
        try:
            self.enqueue(job.id)
        except QueueUnavailable:
            self.repo.fail_job(job.id, "The worker queue is unavailable; try again shortly.")
            raise ReferenceRequestError("The worker queue is unavailable; try again shortly.", 503) from None
        return job
