"""Reference comparison: ReferenceService's rules, and the officer-only routes with the dedicated login."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from hub_db import AuditEntry
from hub_db.reference import save_comparison
from sqlalchemy import select
from toads_api.reference.login import WclLogin
from toads_api.reference.repository import InMemoryReferenceRepository, StoredComparison, UserToken
from toads_api.reference.service import (
    QueueUnavailable,
    ReferenceRequestError,
    ReferenceService,
    clean_label,
    parse_report,
)

from conftest import HUB, Hub, make_settings

OURS = "OursOursOursOurs"
THEIRS = "TheirsTheirsThei"
WCL = "https://wcl.test"


# ── Rules ──


def _service(queue: list[str] | None = None, *, connected: bool = True) -> ReferenceService:
    repo = InMemoryReferenceRepository()
    if connected:
        repo.save_login(UserToken(secrets.token_urlsafe(8), None, 1.0), 1)
    return ReferenceService(repo, (queue if queue is not None else []).append, configured=True)


@pytest.mark.parametrize(
    "text",
    [
        THEIRS,
        f"  {THEIRS} ",
        f"https://fresh.warcraftlogs.com/reports/{THEIRS}#fight=3",
        f"warcraftlogs.com/reports/{THEIRS}",
    ],
)
def test_report_codes_and_links(text: str) -> None:
    assert parse_report(text) == THEIRS


@pytest.mark.parametrize("text", ["", "short", "x" * 17, f"https://evil.test/reports/{THEIRS}", "a" * 400])
def test_anything_else_is_refused(text: str) -> None:
    with pytest.raises(ReferenceRequestError):
        parse_report(text)


def test_labels_are_trimmed_and_capped() -> None:
    assert clean_label("  World   first ") == "World first"
    assert clean_label("   ") is None and clean_label(None) is None
    with pytest.raises(ReferenceRequestError):
        clean_label("x" * 81)


def test_requests_queue_one_job_each() -> None:
    queue: list[str] = []
    svc = _service(queue)
    imp = svc.request_import("wed", 1, f"https://fresh.warcraftlogs.com/reports/{THEIRS}", " Best ")
    cmp_ = svc.request_compare("wed", 1, OURS, THEIRS)
    lab = svc.request_label("wed", 1, THEIRS, "")
    rm = svc.request_delete("wed", 1, THEIRS)
    assert queue == [imp.id, cmp_.id, lab.id, rm.id]
    assert imp.params == {"report": THEIRS, "label": "Best"} and imp.report == THEIRS
    assert cmp_.report == THEIRS and lab.params["label"] is None
    assert [j.kind for j in svc.overview().jobs] == ["delete", "label", "compare", "import"]


def test_import_needs_a_working_login() -> None:
    with pytest.raises(ReferenceRequestError) as info:
        _service(connected=False).request_import("wed", 1, THEIRS, None)
    assert info.value.status == 409
    svc = _service()
    assert isinstance(svc.repo, InMemoryReferenceRepository)
    svc.repo.expired = True
    with pytest.raises(ReferenceRequestError, match="expired"):
        svc.request_import("wed", 1, THEIRS, None)


def test_a_raid_is_not_compared_with_itself() -> None:
    with pytest.raises(ReferenceRequestError):
        _service().request_compare("wed", 1, THEIRS, THEIRS)


def test_a_full_queue_fails_the_job() -> None:
    def refuse(_: str) -> None:
        raise QueueUnavailable

    svc = _service()
    svc.enqueue = refuse
    with pytest.raises(ReferenceRequestError) as info:
        svc.request_delete("wed", 1, THEIRS)
    assert info.value.status == 503
    assert svc.overview().jobs[0].status == "failed"


def test_unconfigured_hub_says_so() -> None:
    svc = ReferenceService(InMemoryReferenceRepository(), [].append, configured=False)
    with pytest.raises(ReferenceRequestError) as info:
        svc.require_configured()
    assert info.value.status == 503


# ── Routes ──


class FakeWcl:
    """Warcraft Logs' token endpoint."""

    def __init__(self) -> None:
        self.status = 200
        self.seen: list[dict[str, list[str]]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{WCL}/oauth/token"
        self.seen.append(parse_qs(request.content.decode()))
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "invalid_grant"})
        return httpx.Response(
            200, json={"access_token": secrets.token_urlsafe(16), "refresh_token": "r", "expires_in": 3600}
        )


@pytest.fixture
def wired(hub: Hub) -> tuple[Hub, FakeWcl, list[str]]:
    wcl = FakeWcl()
    settings = make_settings(wcl_client_id="toads-wcl", wcl_client_secret=secrets.token_urlsafe(12), wcl_site_url=WCL)
    hub.services.wcl_login = WclLogin(settings, hub.redis, httpx.AsyncClient(transport=httpx.MockTransport(wcl)))
    hub.services.reference.configured = True
    queued: list[str] = []
    hub.services.reference.enqueue = queued.append
    return hub, wcl, queued


def _connect(hub: Hub, sid: str, day: str = "wed") -> httpx.Response:
    start = hub.post(f"/api/days/{day}/reference/login", sid)
    assert start.status_code == 200, start.text
    url = urlparse(start.json()["authorize_url"])
    query = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{WCL}/oauth/authorize"
    assert query["redirect_uri"] == [f"{HUB}/api/reference/login/callback"] and query["client_id"] == ["toads-wcl"]
    return hub.client.get(
        f"/api/reference/login/callback?code=abc&state={query['state'][0]}",
        headers=hub.as_(sid),
        follow_redirects=False,
    )


def test_an_officer_connects_the_login_and_imports(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, wcl, queued = wired
    sid = hub.login(hub.user(("wed", "officer"), nick="Hopscotch"))
    before = hub.get("/api/days/wed/reference", sid).json()
    assert before["login"] == {
        "configured": True,
        "connected": False,
        "status": None,
        "connected_by": None,
        "connected_at": None,
    }
    assert before["references"] == [] and before["generated_at"] is None

    back = _connect(hub, sid)
    assert back.status_code == 303
    assert back.headers["location"] == f"{HUB}/officers/reference/?day=wed&login=ok"
    assert wcl.seen[0]["grant_type"] == ["authorization_code"] and wcl.seen[0]["code"] == ["abc"]

    login = hub.get("/api/days/wed/reference", sid).json()["login"]
    assert login["connected"] and login["status"] == "working" and login["connected_by"] == "Hopscotch"

    r = hub.post("/api/days/wed/reference/imports", sid, {"report": THEIRS, "label": "World first"})
    assert r.status_code == 202, r.text
    assert queued == [r.json()["id"]]
    jobs = hub.get("/api/days/wed/reference", sid).json()["jobs"]
    assert [(j["kind"], j["status"], j["report"]) for j in jobs] == [("import", "queued", THEIRS)]
    with hub.db() as db:
        actions = [a.action for a in db.scalars(select(AuditEntry))]
    assert "reference.connect" in actions and "reference.import" in actions


def test_members_raiders_and_other_days_officers_are_refused(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, _, _ = wired
    for roles in ((), (("wed", "raider"),), (("sun", "officer"),)):
        sid = hub.login(hub.user(*roles))
        assert hub.get("/api/days/wed/reference", sid).status_code == 403
        assert hub.post("/api/days/wed/reference/login", sid).status_code == 403
    assert hub.get("/api/days/wed/reference", None).status_code == 401


def test_a_global_officer_uses_any_day(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, _, _ = wired
    sid = hub.login(hub.user(("global", "officer")))
    assert hub.get("/api/days/sun/reference", sid).status_code == 200


def test_the_login_callback_is_single_use_and_bound_to_the_officer(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, wcl, _ = wired
    officer = hub.login(hub.user(("wed", "officer")))
    start = hub.post("/api/days/wed/reference/login", officer).json()["authorize_url"]
    state = parse_qs(urlparse(start).query)["state"][0]

    other = hub.login(hub.user(("wed", "officer")))
    r = hub.client.get(f"/api/reference/login/callback?code=abc&state={state}", headers=hub.as_(other))
    assert r.status_code == 403
    # The state was spent by that attempt.
    r = hub.client.get(
        f"/api/reference/login/callback?code=abc&state={state}", headers=hub.as_(officer), follow_redirects=False
    )
    assert r.headers["location"] == f"{HUB}/officers/reference/?login=failed"
    assert wcl.seen == []


def test_a_refused_code_or_a_cancel_connects_nothing(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, wcl, _ = wired
    sid = hub.login(hub.user(("wed", "officer")))
    wcl.status = 400
    assert _connect(hub, sid).headers["location"].endswith("login=failed")
    start = hub.post("/api/days/wed/reference/login", sid).json()["authorize_url"]
    state = parse_qs(urlparse(start).query)["state"][0]
    r = hub.client.get(f"/api/reference/login/callback?state={state}", headers=hub.as_(sid), follow_redirects=False)
    assert r.headers["location"].endswith("login=cancelled")
    assert not hub.get("/api/days/wed/reference", sid).json()["login"]["connected"]


def test_disconnect(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, _, _ = wired
    sid = hub.login(hub.user(("wed", "officer")))
    _connect(hub, sid)
    assert hub.delete("/api/days/wed/reference/login", sid).status_code == 204
    assert not hub.get("/api/days/wed/reference", sid).json()["login"]["connected"]
    assert hub.post("/api/days/wed/reference/imports", sid, {"report": THEIRS}).status_code == 409


def test_requests_refuse_bad_input(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, _, queued = wired
    sid = hub.login(hub.user(("wed", "officer")))
    _connect(hub, sid)
    assert hub.post("/api/days/wed/reference/imports", sid, {"report": "nope"}).status_code == 400
    assert hub.post("/api/days/wed/reference/imports", sid, {"report": THEIRS, "label": "x" * 90}).status_code == 400
    assert hub.post("/api/days/wed/reference/comparisons", sid, {"guild_report": OURS}).status_code == 422
    assert hub.delete("/api/days/wed/reference/references/nope", sid).status_code == 400
    assert queued == []


def test_compare_label_delete_and_read_a_comparison(wired: tuple[Hub, FakeWcl, list[str]]) -> None:
    hub, _, queued = wired
    sid = hub.login(hub.user(("wed", "officer")))
    r = hub.post("/api/days/wed/reference/comparisons", sid, {"guild_report": OURS, "reference_report": THEIRS})
    assert r.status_code == 202 and r.json()["kind"] == "compare"
    r = hub.client.put(
        f"/api/days/wed/reference/references/{THEIRS}/label", headers=hub.as_(sid), json={"label": "Best"}
    )
    assert r.status_code == 202 and r.json()["kind"] == "label"
    assert hub.delete(f"/api/days/wed/reference/references/{THEIRS}", sid).status_code == 202
    assert len(queued) == 3

    path = f"/api/days/wed/reference/comparisons/{OURS}/{THEIRS}"
    assert hub.get(path, sid).status_code == 404
    payload: dict[str, Any] = {
        "version": 1,
        "guild": {"report_id": OURS, "title": "Toads Gruul"},
        "reference": {"report_id": THEIRS, "title": "Best Gruul"},
    }
    with hub.db.begin() as db:
        save_comparison(db, payload, "2026-09-28 10:00:00")
    got = hub.get(path, sid).json()
    assert got == {"generated_at": "2026-09-28 10:00:00", "comparison": payload}
    listed = hub.get("/api/days/wed/reference", sid).json()["comparisons"]
    assert listed == [
        {
            "guild_report": OURS,
            "reference_report": THEIRS,
            "guild_title": "Toads Gruul",
            "reference_title": "Best Gruul",
            "generated_at": "2026-09-28 10:00:00",
        }
    ]


def test_an_unconfigured_hub_cannot_start_a_login(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    assert hub.get("/api/days/wed/reference", sid).json()["login"]["configured"] is False
    assert hub.post("/api/days/wed/reference/login", sid).status_code == 503


def test_stored_comparison_round_trips_in_memory() -> None:
    repo = InMemoryReferenceRepository()
    repo.stored[(OURS, THEIRS)] = StoredComparison("t", {"guild": {"title": "a"}, "reference": {"title": "b"}})
    svc = ReferenceService(repo, [].append, configured=True)
    assert svc.comparison(OURS, THEIRS) == repo.stored[(OURS, THEIRS)]
    assert svc.overview().comparisons[0].guild_title == "a"
