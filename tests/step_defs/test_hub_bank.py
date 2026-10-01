"""REQ-HUB-BANK-021..041 and REQ-HUB-RBAC-003..004: the hub's adapter to ToadsBank, its bank grants, officer tokens,
super admins and the break-glass admin, against the in-memory fake (docs/bank.md, docs/admin.md)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from hub_db import AuditEntry, BankGrantToken, Base
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenario, scenarios, then, when
from sqlalchemy import select
from toads_api.bank.client import BankClient
from toads_api.bank.events import BOT, DM, POST, BankEvents
from toads_api.bank_grants.routes import REDEEM_ATTEMPTS
from toads_api.bank_grants.service import REFUSED, hash_token
from toads_api.bots.models import ActionResult
from toads_api.testing.fake_bank import FakeBankState, create_fake_bank, encode_parts, sample_snapshot, seeded_state
from toads_api.testing.fake_discord import FakeUser

from conftest import Hub, make_settings

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_bank.feature"))
RBAC_FEATURE = str(FEATURES / "hub_rbac.feature")


def _rbac_title(number: int) -> str:
    prefix = f"Scenario: REQ-HUB-RBAC-{number:03d} "
    line = next(x for x in Path(RBAC_FEATURE).read_text(encoding="utf-8").splitlines() if prefix in x)
    return line.split("Scenario: ", 1)[1]


@scenario(RBAC_FEATURE, _rbac_title(3))
def test_rbac_003_super_admins() -> None:
    pass


@scenario(RBAC_FEATURE, _rbac_title(4))
def test_rbac_004_break_glass() -> None:
    pass


# Built at runtime: a literal token-looking string trips the secret scanners.
TOKEN = "-".join(("bdd", "bank", "token"))
HUB_TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
BOT_TOKEN = "-".join(("bdd", "bank", "bot"))
BANK_URL = "http://bank.test"


class Recording(httpx.AsyncBaseTransport):
    """Passes every call on to the fake ToadsBank and remembers it, so a step can check what ToadsBank heard."""

    def __init__(self, inner: httpx.AsyncBaseTransport, seen: list[httpx.Request]) -> None:
        self.inner = inner
        self.seen = seen

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        return await self.inner.handle_async_request(request)


class World:
    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.officer_user = hub.user(("wed", "officer"), nick="Ribbit")
        self.member_user = hub.user(nick="Hopscotch")
        self.global_user = hub.user(("global", "officer"), nick="Croak")
        self.sunday_officer_user = hub.user(("sun", "officer"), nick="Bufo")
        # A plain member a super admin grants part of the bank's upkeep to.
        self.grantee_user = hub.user(nick="Tadpole")
        # Named in configuration (docs/admin.md): a super admin, and the break-glass admin.
        self.super_user = hub.user(nick="Lilypad")
        self.glass_user = hub.user(nick="Glass")
        self.grant_id = 0
        self.token = ""
        self.token_id = 0
        self.refusals = 0
        self.sunday: dict[str, Any] = {}
        self.state: FakeBankState | None = None
        self.seen: list[httpx.Request] = []
        self.response: httpx.Response | None = None
        self.request: dict[str, Any] = {}
        self.import_id = ""
        self.parts: list[str] = []
        self.progress: dict[str, Any] = {}
        self.keys = 0

    def configure(self, transport: httpx.AsyncBaseTransport) -> None:
        self.hub.services.settings = make_settings(
            bank_url=BANK_URL,
            bank_service_token=TOKEN,
            bank_bot_token=BOT_TOKEN,
            super_admin_ids=str(self.super_user.user_id),
            break_glass_admin_id=str(self.glass_user.user_id),
        )
        self.hub.services.bank = BankClient(httpx.AsyncClient(transport=transport), BANK_URL, SecretStr(TOKEN))

    def fake(self) -> None:
        self.state = seeded_state(
            manager=str(self.officer_user.user_id), raid_day="wed", token=TOKEN, clock=lambda: self.hub.now
        )
        self.configure(Recording(httpx.ASGITransport(app=create_fake_bank(self.state)), self.seen))

    def session(self, user: FakeUser) -> str:
        return self.hub.login(user)

    def key(self) -> dict[str, str]:
        self.keys += 1
        return {"Idempotency-Key": f"bdd-{self.keys}"}

    def get(self, path: str, session: str, **params: str) -> httpx.Response:
        return self.hub.client.get(path, headers=self.hub.as_(session), params=params)

    def post(self, path: str, session: str, body: Any = None) -> httpx.Response:
        return self.hub.client.post(path, headers={**self.hub.as_(session), **self.key()}, json=body or {})

    def ask(self, session: str, quantity: int, **extra: Any) -> httpx.Response:
        assert self.state is not None
        source = next(iter(self.state.sources))
        body = {"sourceId": source, "itemId": 22832, "quantity": quantity, "character": "Frogmage", **extra}
        return self.post("/api/bank/requests", session, body)

    def event(self, event_id: str, kind: str, payload: dict[str, Any], token: str = TOKEN) -> httpx.Response:
        body = {"id": event_id, "type": kind, "occurredAt": 1, "payload": payload}
        return self.hub.client.post("/api/bank/events", json=body, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def world(hub: Hub) -> World:
    return World(hub)


def _request(**extra: Any) -> dict[str, Any]:
    return {
        "id": "req_1",
        "revision": 2,
        "memberId": "5678",
        "memberName": "Frogger",
        "character": "Frogmage",
        "itemName": "Super Mana Potion",
        "quantity": 5,
        **extra,
    }


# --------------------------------------------------------------------- setup


@given("the guild bank is set up with one captured bank")
def bank_set_up(world: World) -> None:
    world.fake()


@given("ToadsBank is listening")
def listening(world: World) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        world.seen.append(request)
        return httpx.Response(201 if request.method == "POST" else 200, json=[] if request.method == "GET" else {})

    world.configure(httpx.MockTransport(handler))


@given("a hub without the bank configured")
def not_configured(world: World) -> None:
    assert world.hub.services.bank is None


@given("ToadsBank is down")
def down(world: World) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    world.configure(httpx.MockTransport(handler))


@given(parsers.parse("the bank bot's fallback channel is {channel:d}"))
def fallback_channel(world: World, channel: int) -> None:
    world.hub.services.bank_events = BankEvents(world.hub.services.bots, fallback_channel=channel)


# ------------------------------------------------------------- REQ-BANK-021


@when("a member opens the bank")
def opens_bank(world: World) -> None:
    session = world.session(world.member_user)
    world.response = world.get("/api/bank/sources", session)
    world.progress = world.get("/api/bank/inventory", session).json()


@then(parsers.parse('they see "{name}" marked fresh with its observation time'))
def sees_source(world: World, name: str) -> None:
    assert world.response is not None
    [source] = world.response.json()
    assert (source["name"], source["freshness"]) == (name, "fresh")
    assert source["lastObservedAt"] <= world.hub.now


@then(
    parsers.parse(
        'the inventory shows {observed:d} "{name}" observed and {available:d} available with a capture-time range'
    )
)
def inventory_shows(world: World, observed: int, name: str, available: int) -> None:
    [item] = [i for i in world.progress["items"] if i["name"] == name]
    assert (item["observed"], item["available"]) == (observed, available)
    assert {"pendingOutgoing", "raidHeld", "directReserved"} <= set(item)
    assert world.progress["range"]["oldest"] <= world.progress["range"]["newest"]


# ------------------------------------------------------------- REQ-BANK-022


@when(parsers.parse('a member requests {quantity:d} "{name}"'))
def member_requests(world: World, quantity: int, name: str) -> None:
    world.response = world.ask(world.session(world.member_user), quantity)


@then("the request is refused as insufficient stock with the waitlist offered")
def refused_for_stock(world: World) -> None:
    assert world.response is not None and world.response.status_code == 409
    error = world.response.json()["error"]
    assert (error["code"], error["details"]["canWaitlist"]) == ("insufficient_stock", True)


@when("the member asks for the waitlist instead")
def waitlist(world: World) -> None:
    world.response = world.ask(world.session(world.member_user), 500, waitlist=True)


@then("their request is waitlisted in their own name")
def waitlisted(world: World) -> None:
    assert world.response is not None and world.response.status_code == 201
    created = world.response.json()
    assert (created["status"], created["memberId"]) == ("waitlisted", str(world.member_user.user_id))


# ------------------------------------------------------------- REQ-BANK-023


@given(parsers.parse('a member has requested {quantity:d} "{name}"'))
def has_requested(world: World, quantity: int, name: str) -> None:
    world.request = world.ask(world.session(world.member_user), quantity).json()


@when(parsers.parse("the member cancels it with {which} revision"))
def cancels(world: World, which: str) -> None:
    revision = world.request["revision"] - 1 if which == "an old" else world.request["revision"]
    path = f"/api/bank/requests/{world.request['id']}/cancel"
    world.response = world.post(path, world.session(world.member_user), {"expectedRevision": revision})


@then("the hub refuses it as stale and shows the current revision")
def stale(world: World) -> None:
    assert world.response is not None and world.response.status_code == 409
    error = world.response.json()["error"]
    assert (error["code"], error["current"]["revision"]) == ("stale_revision", world.request["revision"])


@then("the request is cancelled and the stock is free again")
def cancelled(world: World) -> None:
    assert world.response is not None and world.response.json()["status"] == "cancelled"
    items = world.get("/api/bank/inventory", world.session(world.member_user), q="Super Mana").json()["items"]
    assert items[0]["available"] == items[0]["observed"]


# ------------------------------------------------------------- REQ-BANK-024


@when("a Wednesday officer pastes the first part of a new export")
def first_part(world: World) -> None:
    snapshot = sample_snapshot(int(world.hub.now) - 60, "spineshatter-bankalt-bdd-0001")
    snapshot["tabs"][0]["slots"] *= 20
    world.parts = encode_parts(snapshot)
    session = world.session(world.officer_user)
    world.import_id = world.post("/api/days/wed/bank/imports", session).json()["id"]
    path = f"/api/days/wed/bank/imports/{world.import_id}/parts"
    world.progress = world.post(path, session, {"text": world.parts[0]}).json()


@then("the hub reports that part received and the rest missing")
def reported(world: World) -> None:
    total = len(world.parts)
    assert (world.progress["received"], world.progress["missing"]) == ([1], list(range(2, total + 1)))


@when("the officer pastes the remaining parts in reverse order")
def remaining(world: World) -> None:
    path = f"/api/days/wed/bank/imports/{world.import_id}/parts"
    text = "\n\n".join(reversed(world.parts[1:]))
    world.progress = world.post(path, world.session(world.officer_user), {"text": text}).json()
    assert world.progress["complete"]


@then(parsers.parse('the preview names "{name}" and warns that tab 3 was not readable'))
def previewed(world: World, name: str) -> None:
    path = f"/api/days/wed/bank/imports/{world.import_id}/preview"
    preview = world.get(path, world.session(world.officer_user)).json()
    assert preview["matchedSource"]["name"] == name
    assert preview["warnings"] == ["tab 3 was not readable"]


@then("accepting it updates tabs 1 and 2 and keeps tab 3 as it was")
def accepted(world: World) -> None:
    path = f"/api/days/wed/bank/imports/{world.import_id}/accept"
    receipt = world.post(path, world.session(world.officer_user)).json()
    assert (receipt["tabsUpdated"], receipt["tabsNotRead"]) == ([1, 2], [3])


# ------------------------------------------------------------- REQ-BANK-025


@when(parsers.parse("ToadsBank reports a request assigned to managers {first:d} and {second:d}"))
def assigned(world: World, first: int, second: int) -> None:
    payload = {"request": _request(), "managers": [str(first), str(second)]}
    assert world.event("evt_assigned", "request.assigned", payload).status_code == 200


@then(parsers.parse("the bank bot is asked to DM {first:d} and {second:d} with buttons for revision {revision:d}"))
def dms_asked(world: World, first: int, second: int, revision: int) -> None:
    actions = world.hub.services.bots.pending(BOT)
    assert [(a.kind, a.payload["user_id"]) for a in actions] == [(DM, str(first)), (DM, str(second))]
    assert all(a.payload["manage"] == {"request_id": "req_1", "revision": revision} for a in actions)


@when(parsers.parse("every attempt to DM {user:d} fails"))
def dm_fails(world: World, user: int) -> None:
    bots = world.hub.services.bots
    [action] = [a for a in bots.pending(BOT) if a.payload.get("user_id") == str(user)]
    for _ in range(5):
        bots.complete(BOT, action.id, ActionResult(ok=False, error="Forbidden"))


@then(parsers.parse("the bank bot is asked to post in channel {channel:d} that a manager could not be reached"))
def fallback_posted(world: World, channel: int) -> None:
    [post] = [a for a in world.hub.services.bots.pending(BOT) if a.kind == POST]
    assert post.payload["channel_id"] == str(channel)
    assert "could not be reached by DM" in post.payload["content"]


# ------------------------------------------------------------- REQ-BANK-026


@then("an event sent with the hub's own bot token is refused with 401")
def wrong_token(world: World) -> None:
    assert world.event("evt_x", "request.created", {}, token=HUB_TOKEN).status_code == 401


@when("ToadsBank sends the same request update twice")
def twice(world: World) -> None:
    payload = {"request": _request(status="approved"), "change": "approved"}
    assert world.event("evt_twice", "request.updated", payload).json()["duplicate"] is False
    assert world.event("evt_twice", "request.updated", payload).json()["duplicate"] is True


@then("the requester is DMed once")
def dmed_once(world: World) -> None:
    assert [a.payload["user_id"] for a in world.hub.services.bots.pending(BOT)] == ["5678"]


# ------------------------------------------------------------- REQ-BANK-027


@when(parsers.parse('a global officer called "{name}" asks for the bank\'s sources and makes a request'))
def global_officer_calls(world: World, name: str) -> None:
    officer = world.hub.user(("global", "officer"), nick=name)
    world.officer_user = officer
    session = world.session(officer)
    assert world.get("/api/bank/sources", session).status_code == 200
    body = {"sourceId": "src_1", "itemId": 1, "quantity": 1, "character": "Frogmage"}
    r = world.hub.client.post(
        "/api/bank/requests", headers={**world.hub.as_(session), "Idempotency-Key": "sent-key"}, json=body
    )
    assert r.status_code == 201


@then(parsers.parse('ToadsBank hears the service token, their Discord id, "{name}" and the roles "{roles}"'))
def hears_identity(world: World, name: str, roles: str) -> None:
    assert len(world.seen) == 2
    for request in world.seen:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert request.headers["X-Toads-Member"] == str(world.officer_user.user_id)
        assert (request.headers["X-Toads-Name"], request.headers["X-Toads-Roles"]) == (name, roles)


@then("the idempotency key it hears is not the one the officer sent")
def derived_key(world: World) -> None:
    key = world.seen[1].headers["Idempotency-Key"]
    assert key != "sent-key" and len(key) == 64


# ------------------------------------------------------------- REQ-BANK-028


@then(parsers.parse('a member asking for the bank\'s sources gets {status:d} "{code}"'))
def answers(world: World, status: int, code: str) -> None:
    r = world.get("/api/bank/sources", world.session(world.member_user))
    assert (r.status_code, r.json()["error"]["code"]) == (status, code)


# ------------------------------------------------------------- REQ-BANK-029


@when(parsers.parse('ToadsBank reports a request from "{member}" for "{item}" approved'))
def approved_with_names(world: World, member: str, item: str) -> None:
    payload = {"request": _request(memberName=member, character=member, itemName=item), "change": "approved"}
    world.event("evt_names", "request.updated", payload)


@then("the DM shows both names as written, with their markdown and mention syntax escaped")
def escaped(world: World) -> None:
    [action] = world.hub.services.bots.pending(BOT)
    content = action.payload["content"]
    assert "\\@everyone" in content and "Super \\*Mana\\* Potion" in content
    assert "@everyone" not in content.replace("\\@everyone", "")


@then("the bank bot sends it with mentions suppressed")
def no_pings() -> None:
    import discord
    from toads_bot.kit.bank import NO_PINGS

    assert NO_PINGS.everyone is False and NO_PINGS.users is False and NO_PINGS.roles is False
    assert NO_PINGS.to_dict() == discord.AllowedMentions.none().to_dict()


# ------------------------------------------------------------- REQ-BANK-030


def _acting_open(world: World, user: FakeUser | int, token: str = BOT_TOKEN) -> int:
    member = user.user_id if isinstance(user, FakeUser) else user
    headers = {"Authorization": f"Bearer {token}", "X-Toads-Acting-Member": str(member), **world.key()}
    return world.hub.client.post("/api/days/wed/bank/imports", headers=headers).status_code


@then("the bot acting for a Wednesday officer may open an import for Wednesday")
def acting_officer(world: World) -> None:
    assert _acting_open(world, world.officer_user) == 201


@then("the bot acting for a plain member may not")
def acting_member(world: World) -> None:
    assert _acting_open(world, world.member_user) == 403


@then("the bot acting for someone outside the server is refused")
def acting_stranger(world: World) -> None:
    assert _acting_open(world, 424242) == 403


@then("a caller with the hub's shared service token may not act for anyone")
def acting_with_the_shared_token(world: World) -> None:
    assert _acting_open(world, world.officer_user, token=HUB_TOKEN) == 401


# ------------------------------------------------------------- REQ-BANK-031


@given("a second bank assigned to Sunday that ToadsBank lets the Wednesday officer manage")
def sunday_bank(world: World) -> None:
    assert world.state is not None
    world.sunday = world.state.add_source(
        name="Sunday bank",
        guild="Toads Sunday",
        realm="Spineshatter",
        region="EU",
        managers=[str(world.officer_user.user_id)],
        raidDay="sun",
    )
    world.state.store_snapshot(world.sunday["id"], sample_snapshot(int(world.hub.now) - 3600))


@when("a member requests an item from the Sunday bank")
def request_from_sunday(world: World) -> None:
    body = {"sourceId": world.sunday["id"], "itemId": 22832, "quantity": 5, "character": "Frogmage"}
    world.request = world.post("/api/bank/requests", world.session(world.member_user), body).json()


@then("the Wednesday officer's queue for Wednesday leaves that request out")
def queue_leaves_it_out(world: World) -> None:
    queue = world.get("/api/days/wed/bank/requests", world.session(world.officer_user)).json()
    assert world.request["id"] not in [r["id"] for r in queue]


@then("the Wednesday officer may not approve it through Wednesday")
def officer_refused(world: World) -> None:
    path = f"/api/days/wed/bank/requests/{world.request['id']}/approve"
    r = world.post(path, world.session(world.officer_user), {"expectedRevision": 1})
    assert (r.status_code, r.json()["error"]["code"]) == (403, "not_this_day")


@then("a global officer may approve it through Wednesday")
def global_officer_approves(world: World) -> None:
    path = f"/api/days/wed/bank/requests/{world.request['id']}/approve"
    r = world.post(path, world.session(world.global_user), {"expectedRevision": 1})
    assert r.json()["status"] == "approved"


# ------------------------------------------------------- REQ-BANK-032..036

GRANTS = "/api/admin/bank/grants"
TOKENS = "/api/admin/bank/tokens"


def _grant(world: World, permission: str, day: str | None, by: FakeUser | None = None) -> httpx.Response:
    body = {"discord_user_id": str(world.grantee_user.user_id), "permission": permission, "raid_day": day}
    return world.post(GRANTS, world.session(by or world.super_user), body)


@given(parsers.parse('a super admin has granted the grantee "{permission}" for "{day}"'))
@when(parsers.parse('a super admin grants the grantee "{permission}" for "{day}"'))
def grants_for_day(world: World, permission: str, day: str) -> None:
    r = _grant(world, permission, day)
    assert r.status_code == 201, r.text
    world.grant_id = r.json()["id"]


@given(parsers.parse('a super admin has granted the grantee "{permission}" for every bank'))
def grants_everywhere(world: World, permission: str) -> None:
    r = _grant(world, permission, None)
    assert r.status_code == 201, r.text
    world.grant_id = r.json()["id"]


@then(parsers.parse('the grantee\'s bank standing lists "{day}" to import and nothing to manage'))
def standing_imports(world: World, day: str) -> None:
    me = world.get("/api/bank/me", world.session(world.grantee_user)).json()
    assert (me["officer_days"], me["import_days"], me["manage_days"], me["manages_grants"]) == ([], [day], [], False)


@then("the grantee's bank standing lists every raid day to manage and nothing to import")
def standing_manages_everywhere(world: World) -> None:
    me = world.get("/api/bank/me", world.session(world.grantee_user)).json()
    assert (me["import_days"], me["manage_days"]) == ([], ["wed", "sun"])


@then("the grantee may not list or work an officers-only bank's requests")
def grantee_never_sees_hidden(world: World) -> None:
    """Qodo 4152357910: a grant to work the queue never makes an officers-only bank visible."""
    assert world.state is not None
    hidden = world.state.add_source(
        name="Officers bank", guild="Toads Officers", realm="Spineshatter", region="EU", audience="officers"
    )
    world.state.store_snapshot(hidden["id"], sample_snapshot(int(world.hub.now) - 3600))
    officer_ask = world.post(
        "/api/bank/requests",
        world.session(world.global_user),
        {"sourceId": hidden["id"], "itemId": 22832, "quantity": 1, "character": "Frogmage"},
    )
    assert officer_ask.status_code == 201, officer_ask.text
    session = world.session(world.grantee_user)
    for day in ("wed", "sun"):
        for scope in ("queue", "all"):
            rows = world.get(f"/api/days/{day}/bank/requests", session, scope=scope).json()
            assert hidden["id"] not in {r.get("sourceId") for r in rows}, (day, scope)
    approve = f"/api/days/wed/bank/requests/{officer_ask.json()['id']}/approve"
    assert world.post(approve, session, {"expectedRevision": 1}).status_code in (403, 404)


@then("the grantee may import and accept a Wednesday export")
def grantee_imports(world: World) -> None:
    session = world.session(world.grantee_user)
    snapshot = sample_snapshot(int(world.hub.now) - 30, "spineshatter-bankalt-bdd-0032")
    import_id = world.post("/api/days/wed/bank/imports", session).json()["id"]
    added = world.post(
        f"/api/days/wed/bank/imports/{import_id}/parts", session, {"text": "\n".join(encode_parts(snapshot))}
    )
    assert added.json()["complete"], added.text
    world.seen.clear()
    receipt = world.post(f"/api/days/wed/bank/imports/{import_id}/accept", session)
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["duplicate"] is False


@then(parsers.parse('ToadsBank heard the grantee as "{roles}"'))
def heard_grantee(world: World, roles: str) -> None:
    accepts = [r for r in world.seen if r.url.path.endswith("/accept")]
    assert accepts and {r.headers["X-Toads-Roles"] for r in accepts} == {roles}
    assert {r.headers["X-Toads-Member"] for r in accepts} == {str(world.grantee_user.user_id)}


@then("the grantee may not open an import through Sunday")
def grantee_not_sunday(world: World) -> None:
    assert world.post("/api/days/sun/bank/imports", world.session(world.grantee_user)).status_code == 403


@then("the grantee may not list the Wednesday request queue on the site")
def grantee_no_queue(world: World) -> None:
    assert world.get("/api/days/wed/bank/requests", world.session(world.grantee_user)).status_code == 403


@then("a Sunday officer that ToadsBank does not list as a manager may approve it through Sunday")
def sunday_officer_approves(world: World) -> None:
    assert str(world.sunday_officer_user.user_id) not in world.sunday["managers"]
    world.seen.clear()
    path = f"/api/days/sun/bank/requests/{world.request['id']}/approve"
    r = world.post(path, world.session(world.sunday_officer_user), {"expectedRevision": 1})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


@then(parsers.parse('ToadsBank heard the Sunday officer as "{roles}"'))
def heard_sunday_officer(world: World, roles: str) -> None:
    approvals = [r for r in world.seen if r.url.path.endswith("/approve")]
    assert approvals and {r.headers["X-Toads-Roles"] for r in approvals} == {roles}


def _acting_queue(world: World, user: FakeUser) -> int:
    headers = {"Authorization": f"Bearer {BOT_TOKEN}", "X-Toads-Acting-Member": str(user.user_id)}
    return world.hub.client.get("/api/days/wed/bank/requests", headers=headers).status_code


@then("the bot acting for the grantee may list the Wednesday request queue")
def acting_grantee_lists(world: World) -> None:
    assert _acting_queue(world, world.grantee_user) == 200


@when("the super admin revokes that grant")
def revokes(world: World) -> None:
    r = world.hub.client.delete(f"{GRANTS}/{world.grant_id}", headers=world.hub.as_(world.session(world.super_user)))
    assert r.status_code == 204, r.text


@then("the bot acting for the grantee may not list the Wednesday request queue")
def acting_grantee_refused(world: World) -> None:
    # The grantee's Discord roles are still remembered for the bot (REQ-HUB-RBAC-002); their grants never are.
    assert _acting_queue(world, world.grantee_user) == 403


@then("the grantee may approve it through Wednesday")
def grantee_approves_anywhere(world: World) -> None:
    path = f"/api/days/wed/bank/requests/{world.request['id']}/approve"
    r = world.post(path, world.session(world.grantee_user), {"expectedRevision": 1})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


def _grant_routes_refused(world: World, user: FakeUser) -> None:
    session = world.session(user)
    body = {"discord_user_id": str(user.user_id), "permission": "manage_bank", "raid_day": "wed"}
    assert world.get(GRANTS, session).status_code == 403
    assert world.post(GRANTS, session, body).status_code == 403
    assert world.hub.client.delete(f"{GRANTS}/{world.grant_id}", headers=world.hub.as_(session)).status_code == 403


@then("a Wednesday officer may not list, grant or revoke bank grants")
def officer_cannot_grant(world: World) -> None:
    _grant_routes_refused(world, world.officer_user)


@then("the grantee may not list, grant or revoke bank grants")
def grantee_cannot_grant(world: World) -> None:
    _grant_routes_refused(world, world.grantee_user)
    assert [g["id"] for g in world.get(GRANTS, world.session(world.super_user)).json()] == [world.grant_id]


@then("a global officer may list bank grants but not grant or revoke them")
def global_officer_lists_only(world: World) -> None:
    session = world.session(world.global_user)
    assert world.get(GRANTS, session).status_code == 200
    assert _grant(world, "import_bank_snapshot", "sun", by=world.global_user).status_code == 403
    if world.grant_id:
        delete = world.hub.client.delete(f"{GRANTS}/{world.grant_id}", headers=world.hub.as_(session))
        assert delete.status_code == 403
    assert world.post(TOKENS, session, {"permissions": ["manage_bank"]}).status_code == 403


@then("a super admin may not grant someone outside the server")
def stranger_refused(world: World) -> None:
    body = {"discord_user_id": "424242", "permission": "manage_bank", "raid_day": None}
    assert world.post(GRANTS, world.session(world.super_user), body).status_code == 404


@then("a super admin may not grant for an unknown raid day")
def unknown_day_refused(world: World) -> None:
    assert _grant(world, "manage_bank", "fri").status_code == 422


# ------------------------------------------------------------- officer tokens


def _mint(world: World, permission: str, day: str | None, *, by: FakeUser | None = None, **extra: Any) -> None:
    body = {"permissions": [permission], "raid_day": day, **extra}
    r = world.post(TOKENS, world.session(by or world.super_user), body)
    assert r.status_code == 201, r.text
    world.token, world.token_id = r.json()["token"], r.json()["id"]
    world.response = r


@given(parsers.parse('the super admin has minted a token for "{permission}" on "{day}"'))
@when(parsers.parse('the super admin mints a token for "{permission}" on "{day}"'))
def mints(world: World, permission: str, day: str) -> None:
    _mint(world, permission, day)


@when(parsers.parse('the super admin mints a token for "{permission}" on every bank'))
def mints_everywhere(world: World, permission: str) -> None:
    _mint(world, permission, None)


def _tokens(world: World) -> list[dict[str, Any]]:
    r = world.get(TOKENS, world.session(world.super_user))
    assert r.status_code == 200, r.text
    rows: list[dict[str, Any]] = r.json()
    return rows


def _listed(world: World) -> dict[str, Any]:
    return next(t for t in _tokens(world) if t["id"] == world.token_id)


@then("the token is shown once and lasts 7 days")
def shown_once(world: World) -> None:
    assert world.response is not None
    body = world.response.json()
    assert world.token.startswith("toads-bank-") and len(world.token) > 40
    lasts = datetime.fromisoformat(body["expires_at"]) - datetime.fromisoformat(body["minted_at"])
    assert lasts.days == 7 and (body["max_uses"], body["uses"]) == (1, 0)


@then("the token list shows it as active without the token")
def listed_active(world: World) -> None:
    row = _listed(world)
    assert row["status"] == "active" and "token" not in row and row["minted_by_name"]
    assert world.token not in world.get(TOKENS, world.session(world.super_user)).text


@then("only the token's hash is stored")
def hash_only(world: World) -> None:
    with world.hub.db() as db:
        row = db.get(BankGrantToken, world.token_id)
        assert row is not None and row.token_hash == hash_token(world.token)
        assert world.token not in (row.token_hash, row.note)


def _redeem_site(world: World, user: FakeUser, token: str) -> httpx.Response:
    return world.post("/api/bank/redeem", world.session(user), {"token": token})


@when("the bot acting for the grantee redeems the token")
def bot_redeems(world: World) -> None:
    headers = {"Authorization": f"Bearer {BOT_TOKEN}", "X-Toads-Acting-Member": str(world.grantee_user.user_id)}
    r = world.hub.client.post("/api/bank/redeem", headers=headers, json={"token": world.token})
    assert r.status_code == 200, r.text


@given("the member redeems the token on the site")
@when("the member redeems the token on the site")
def member_redeems(world: World) -> None:
    r = _redeem_site(world, world.member_user, world.token)
    assert r.status_code == 200, r.text


@then(parsers.parse('the grantee\'s bank standing lists "{day}" to manage'))
def standing_manages(world: World, day: str) -> None:
    me = world.get("/api/bank/me", world.session(world.grantee_user)).json()
    assert (me["import_days"], me["manage_days"]) == ([], [day])


@then("the member's bank standing lists every raid day to import")
def member_imports_everywhere(world: World) -> None:
    me = world.get("/api/bank/me", world.session(world.member_user)).json()
    assert (me["import_days"], me["manage_days"]) == (["wed", "sun"], [])


@then("the token list shows it used by the grantee")
def listed_used(world: World) -> None:
    row = _listed(world)
    assert (row["status"], row["uses"], row["used_by"]) == ("used", 1, str(world.grantee_user.user_id))
    assert row["used_at"] is not None


@then("the audit log records the redemption under the token's id")
def audited_redemption(world: World) -> None:
    with world.hub.db() as db:
        rows = [a for a in db.scalars(select(AuditEntry)) if a.action == "bank.token_redeemed"]
    assert [a.target for a in rows] == [f"bank token {world.token_id}"]
    assert "manage_bank" in (rows[0].detail or "")


def _refused(world: World, token: str) -> None:
    r = _redeem_site(world, world.grantee_user, token)
    world.refusals += 1
    assert (r.status_code, r.json()["detail"]) == (400, REFUSED), r.text


@then("the grantee redeeming the same token is refused with the one answer")
def same_token_refused(world: World) -> None:
    _refused(world, world.token)


@then("a token past its expiry is refused with the one answer")
def expired_refused(world: World) -> None:
    _mint(world, "manage_bank", "wed", days=1)
    world.hub.pass_time(24 * 3600)
    _refused(world, world.token)


@then("a revoked token is refused with the one answer")
def revoked_refused(world: World) -> None:
    _mint(world, "manage_bank", "wed")
    revoke_token(world)
    _refused(world, world.token)


@then("a made-up token is refused with the one answer")
def made_up_refused(world: World) -> None:
    _refused(world, world.token[:-6] + "abcdef")


@then("the grantee holds no grants")
def holds_nothing(world: World) -> None:
    me = world.get("/api/bank/me", world.session(world.grantee_user)).json()
    assert (me["import_days"], me["manage_days"]) == ([], [])


@then(parsers.parse("after {attempts:d} refusals the grantee must wait"))
def must_wait(world: World, attempts: int) -> None:
    assert attempts == REDEEM_ATTEMPTS
    while world.refusals < attempts:
        _refused(world, "toads-bank-not-a-real-one")
    r = _redeem_site(world, world.grantee_user, world.token)
    assert r.status_code == 429, r.text


@when("the super admin revokes the token")
def revoke_token(world: World) -> None:
    r = world.hub.client.delete(f"{TOKENS}/{world.token_id}", headers=world.hub.as_(world.session(world.super_user)))
    assert r.status_code == 204, r.text


@then("the token list shows it as revoked")
def listed_revoked(world: World) -> None:
    row = _listed(world)
    assert row["status"] == "revoked" and row["revoked_at"] is not None


@then("the super admin may not revoke a used token")
def used_not_revoked(world: World) -> None:
    _mint(world, "manage_bank", "wed")
    member_redeems(world)
    r = world.hub.client.delete(f"{TOKENS}/{world.token_id}", headers=world.hub.as_(world.session(world.super_user)))
    assert r.status_code == 409, r.text


def _token_routes_refused(world: World, user: FakeUser) -> None:
    session = world.session(user)
    assert world.post(TOKENS, session, {"permissions": ["manage_bank"]}).status_code == 403
    assert world.get(TOKENS, session).status_code == 403
    assert world.hub.client.delete(f"{TOKENS}/{world.token_id}", headers=world.hub.as_(session)).status_code == 403
    assert _listed(world)["status"] == "active"


@then("a global officer may not mint, list or revoke officer tokens")
def global_no_tokens(world: World) -> None:
    _token_routes_refused(world, world.global_user)


@then("a Wednesday officer may not mint, list or revoke officer tokens")
def officer_no_tokens(world: World) -> None:
    _token_routes_refused(world, world.officer_user)


@then("the grantee may not mint, list or revoke officer tokens")
def grantee_no_tokens(world: World) -> None:
    _token_routes_refused(world, world.grantee_user)


# ------------------------------------------------- super admins and break glass


@then("the super admin's session reports them as a super admin and a global officer")
def super_session(world: World) -> None:
    info = world.get("/api/session", world.session(world.super_user)).json()
    assert (info["super_admin"], info["global_officer"], info["break_glass"]) == (True, True, False)
    # They hold no Discord officer role: configuration alone makes them one.
    assert world.super_user.roles == set()


@then("the super admin may grant, list and revoke bank grants")
def super_grants(world: World) -> None:
    r = _grant(world, "manage_bank", "wed")
    assert r.status_code == 201, r.text
    world.grant_id = r.json()["id"]
    session = world.session(world.super_user)
    assert [g["id"] for g in world.get(GRANTS, session).json()] == [world.grant_id]
    delete = world.hub.client.delete(f"{GRANTS}/{world.grant_id}", headers=world.hub.as_(session))
    assert delete.status_code == 204, delete.text
    r = _grant(world, "manage_bank", "wed")
    world.grant_id = r.json()["id"]


@then("no route or table makes anyone a super admin")
def nothing_assigns_super_admins(world: World) -> None:
    columns = {c.name for t in Base.metadata.tables.values() for c in t.columns}
    assert not {c for c in columns if "super" in c or "admin" in c}
    paths = {getattr(r, "path", "") for r in world.hub.app.routes}
    assert not {p for p in paths if "super" in p}


@then("the break-glass admin's session and bank standing say break glass")
def glass_shown(world: World) -> None:
    session = world.session(world.glass_user)
    info = world.get("/api/session", session).json()
    assert (info["super_admin"], info["break_glass"]) == (True, True)
    me = world.get("/api/bank/me", session).json()
    assert (me["break_glass"], me["manages_grants"], me["break_glass_admin"]) == (
        True,
        True,
        str(world.glass_user.user_id),
    )


@then("the global tier's bank standing names the break-glass admin")
def glass_named(world: World) -> None:
    me = world.get("/api/bank/me", world.session(world.global_user)).json()
    assert me["break_glass_admin"] == str(world.glass_user.user_id)
    assert world.get("/api/bank/me", world.session(world.member_user)).json()["break_glass_admin"] is None


@when("the break-glass admin mints an officer token")
def glass_mints(world: World) -> None:
    _mint(world, "import_bank_snapshot", None, by=world.glass_user)


@then("the audit log marks the mint as a break-glass change")
def glass_audited(world: World) -> None:
    with world.hub.db() as db:
        rows = [(a.action, a.target) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert ("break_glass", f"POST {TOKENS}") in rows
    assert ("bank.token_minted", f"bank token {world.token_id}") in rows
