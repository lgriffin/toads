"""REQ-HUB-BANK-021..030: the hub's adapter to ToadsBank, against the in-memory fake (docs/bank.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenarios, then, when
from toads_api.bank.client import BankClient
from toads_api.bank.events import BOT, DM, POST, BankEvents
from toads_api.bots.models import ActionResult
from toads_api.testing.fake_bank import FakeBankState, create_fake_bank, encode_parts, sample_snapshot, seeded_state
from toads_api.testing.fake_discord import FakeUser

from conftest import Hub, make_settings

scenarios(str(Path(__file__).resolve().parents[1] / "features" / "hub_bank.feature"))

# Built at runtime: a literal token-looking string trips the secret scanners.
TOKEN = "-".join(("bdd", "bank", "token"))
HUB_TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
BOT_TOKEN = "-".join(("bdd", "bank", "bot"))
BANK_URL = "http://bank.test"


class World:
    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.officer_user = hub.user(("wed", "officer"), nick="Ribbit")
        self.member_user = hub.user(nick="Hopscotch")
        self.global_user = hub.user(("global", "officer"), nick="Croak")
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
            bank_url=BANK_URL, bank_service_token=TOKEN, bank_bot_token=BOT_TOKEN
        )
        self.hub.services.bank = BankClient(httpx.AsyncClient(transport=transport), BANK_URL, SecretStr(TOKEN))

    def fake(self) -> None:
        self.state = seeded_state(
            manager=str(self.officer_user.user_id), raid_day="wed", token=TOKEN, clock=lambda: self.hub.now
        )
        self.configure(httpx.ASGITransport(app=create_fake_bank(self.state)))

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
