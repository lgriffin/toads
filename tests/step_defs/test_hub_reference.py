"""Reference comparison: REQ-HUB-INS-001, 003 to 005. Thin steps over the `hub` fixture (root conftest.py)."""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from hub_db import ReferenceLogin
from pytest_bdd import given, parsers, scenario, then, when
from toads_api.reference.login import WclLogin

from conftest import Hub, make_settings

FEATURES = Path(__file__).resolve().parents[1] / "features"
WCL = "https://wcl.test"
OURS = "OursOursOursOurs"
THEIRS = "TheirsTheirsThei"


def _bind(number: int) -> Any:
    """Bind REQ-HUB-INS-<nnn> from hub_ins.feature (the id is built, not written out)."""
    req_id = f"REQ-HUB-INS-{number:03d}"
    for line in (FEATURES / "hub_ins.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "hub_ins.feature"), m.group(1))
    raise LookupError(req_id)


@_bind(1)
def test_ins_001() -> None:
    pass


@_bind(3)
def test_ins_003() -> None:
    pass


@_bind(4)
def test_ins_004() -> None:
    pass


@_bind(5)
def test_ins_005() -> None:
    pass


@pytest.fixture
def ctx(hub: Hub) -> dict[str, Any]:
    """The hub with a Warcraft Logs application configured, its token endpoint faked, and the queue captured."""
    tokens: list[str] = []

    def wcl(request: httpx.Request) -> httpx.Response:
        token = secrets.token_urlsafe(24)
        tokens.append(token)
        return httpx.Response(200, json={"access_token": token, "refresh_token": token[::-1], "expires_in": 3600})

    settings = make_settings(wcl_client_id="toads-wcl", wcl_client_secret=secrets.token_urlsafe(12), wcl_site_url=WCL)
    hub.services.wcl_login = WclLogin(settings, hub.redis, httpx.AsyncClient(transport=httpx.MockTransport(wcl)))
    hub.services.reference.configured = True
    queued: list[str] = []
    hub.services.reference.enqueue = queued.append
    return {"tokens": tokens, "queued": queued}


@given("a Wednesday officer signed in to the hub")
def officer(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["sid"] = hub.login(hub.user(("wed", "officer"), nick="Hopscotch"))


@then("they can open the Wednesday reference comparison")
def officer_opens(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/reference", ctx["sid"]).status_code == 200


@then(parsers.parse("a {day} {role} cannot open it"))
def others_refused(hub: Hub, day: str, role: str) -> None:
    sid = hub.login(hub.user(({"Wednesday": "wed", "Sunday": "sun"}[day], role)))
    assert hub.get("/api/days/wed/reference", sid).status_code == 403


@given("they connect the guild's Warcraft Logs account")
@when("they connect the guild's Warcraft Logs account")
def connect(hub: Hub, ctx: dict[str, Any]) -> None:
    url = hub.post("/api/days/wed/reference/login", ctx["sid"]).json()["authorize_url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    r = hub.client.get(
        f"/api/reference/login/callback?code=abc&state={state}", headers=hub.as_(ctx["sid"]), follow_redirects=False
    )
    assert r.status_code == 303 and r.headers["location"].endswith("login=ok")


@then("the reference page shows the account connected by them")
def shows_connected(hub: Hub, ctx: dict[str, Any]) -> None:
    login = hub.get("/api/days/wed/reference", ctx["sid"]).json()["login"]
    assert login["connected"] and login["connected_by"] == "Hopscotch"


@then("the database does not hold the token in plain text")
def encrypted(hub: Hub, ctx: dict[str, Any]) -> None:
    with hub.db() as db:
        row = db.get(ReferenceLogin, 1)
        assert row is not None
        stored = row.token_encrypted
    [token] = ctx["tokens"]
    assert token not in stored and token[::-1] not in stored


@when("they import another guild's report as a reference")
def import_reference(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["import"] = hub.post(
        "/api/days/wed/reference/imports", ctx["sid"], {"report": f"https://fresh.warcraftlogs.com/reports/{THEIRS}"}
    )


@when("they compare one of our raids with it")
def compare(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["compare"] = hub.post(
        "/api/days/wed/reference/comparisons", ctx["sid"], {"guild_report": OURS, "reference_report": THEIRS}
    )


@then("both requests are queued for the worker")
def queued(ctx: dict[str, Any]) -> None:
    assert ctx["import"].status_code == 202 and ctx["compare"].status_code == 202
    assert ctx["queued"] == [ctx["import"].json()["id"], ctx["compare"].json()["id"]]


@then("the reference page lists both as queued")
def listed(hub: Hub, ctx: dict[str, Any]) -> None:
    jobs = hub.get("/api/days/wed/reference", ctx["sid"]).json()["jobs"]
    assert [(j["kind"], j["status"]) for j in jobs] == [("compare", "queued"), ("import", "queued")]


@then("the import is refused with 409")
def refused(ctx: dict[str, Any]) -> None:
    assert ctx["import"].status_code == 409
    assert ctx["queued"] == []
