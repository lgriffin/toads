"""The guild bank: the hub's adapter to toadsbank-api (against the in-memory fake), the events webhook and the bank
bot's acting-member calls (docs/bank.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

import httpx
import pytest
from pydantic import SecretStr
from toads_api.bank import messages
from toads_api.bank.client import BankClient, BankError, BankIdentity
from toads_api.bank.events import BOT, DM, POST, BankEvent, BankEvents
from toads_api.bank.routes import derive_key, identity_of
from toads_api.bots.models import ActionResult, BotManifest
from toads_api.rbac import HubRole, Principal
from toads_api.testing.fake_bank import FakeBankState, create_fake_bank, encode_parts, sample_snapshot, seeded_state
from toads_api.testing.fake_discord import FakeUser

from conftest import Hub, make_settings

# Built at runtime: a literal token-looking string trips the secret scanners.
TOKEN = "-".join(("test", "bank", "token"))
HUB_TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
BANK_URL = "http://bank.test"


class Bank:
    """A hub wired to the fake ToadsBank, with a member, a Wednesday officer and a global officer signed in."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.officer_user = hub.user(("wed", "officer"), nick="Ribbit")
        self.member_user = hub.user(nick="Höpscotch *the* @everyone")
        self.global_user = hub.user(("global", "officer"), nick="Croak")
        self.state: FakeBankState = seeded_state(
            manager=str(self.officer_user.user_id), token=TOKEN, clock=lambda: hub.now
        )
        self.fake = create_fake_bank(self.state)
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.fake))
        hub.services.settings = make_settings(bank_url=BANK_URL, bank_service_token=TOKEN)
        hub.services.bank = BankClient(http, BANK_URL, SecretStr(TOKEN))
        self.member = hub.login(self.member_user)
        self.officer = hub.login(self.officer_user)
        self.admin = hub.login(self.global_user)
        self._keys = 0

    def key(self) -> dict[str, str]:
        self._keys += 1
        return {"Idempotency-Key": f"k{self._keys}"}

    def get(self, path: str, session: str, **params: str) -> httpx.Response:
        return self.hub.client.get(path, headers=self.hub.as_(session), params=params)

    def post(self, path: str, session: str, json: Any = None, key: dict[str, str] | None = None) -> httpx.Response:
        headers = {**self.hub.as_(session), **(key if key is not None else self.key())}
        return self.hub.client.post(path, headers=headers, json=json if json is not None else {})

    def source_id(self) -> str:
        return next(iter(self.state.sources))

    def request(self, session: str, quantity: int = 5, **extra: Any) -> httpx.Response:
        body = {"sourceId": self.source_id(), "itemId": 22832, "quantity": quantity, "character": "Frogmage", **extra}
        return self.post("/api/bank/requests", session, body)


@pytest.fixture
def bank(hub: Hub) -> Bank:
    return Bank(hub)


# ------------------------------------------------------------------ members


def test_members_see_sources_inventory_and_the_replica(bank: Bank) -> None:
    [source] = bank.get("/api/bank/sources", bank.member).json()
    assert (source["name"], source["freshness"]) == ("Toads main bank", "fresh")
    inventory = bank.get("/api/bank/inventory", bank.member, q="mana").json()
    [mana] = inventory["items"]
    assert (mana["name"], mana["observed"], mana["available"]) == ("Super Mana Potion", 40, 40)
    assert inventory["range"]["newest"] <= bank.hub.now
    replica = bank.get(f"/api/bank/sources/{source['id']}/replica", bank.member).json()
    assert [t["index"] for t in replica["tabs"]] == [1, 2, 3]
    assert replica["tabs"][0]["slots"][0]["name"] == "Super Mana Potion"


def test_bank_me_says_where_the_caller_is_an_officer(bank: Bank) -> None:
    me = bank.get("/api/bank/me", bank.member).json()
    assert me["configured"] and me["officer_days"] == [] and me["discord_user_id"] == str(bank.member_user.user_id)
    assert bank.get("/api/bank/me", bank.officer).json()["officer_days"] == ["wed"]
    assert bank.get("/api/bank/me", bank.admin).json()["officer_days"] == ["wed", "sun"]


def test_a_request_reserves_stock_in_the_members_name(bank: Bank) -> None:
    r = bank.request(bank.member)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["memberId"] == str(bank.member_user.user_id)
    assert created["memberName"] == "Höpscotch *the* @everyone"  # raw here; escaped wherever the bot speaks
    [mana] = bank.get("/api/bank/inventory", bank.member, q="mana").json()["items"]
    assert (mana["directReserved"], mana["available"]) == (5, 35)
    assert [r["id"] for r in bank.get("/api/bank/requests", bank.member).json()] == [created["id"]]
    assert bank.get("/api/bank/requests", bank.officer).json() == []  # "mine" only


def test_mutating_routes_need_an_idempotency_key(bank: Bank) -> None:
    r = bank.post("/api/bank/requests", bank.member, {"sourceId": "src_1"}, key={})
    assert r.status_code == 422


def test_a_resent_request_is_answered_once(bank: Bank) -> None:
    body = {"sourceId": bank.source_id(), "itemId": 22832, "quantity": 2, "character": "Frogmage"}
    first = bank.post("/api/bank/requests", bank.member, body, key={"Idempotency-Key": "same"})
    again = bank.post("/api/bank/requests", bank.member, body, key={"Idempotency-Key": "same"})
    assert first.json()["id"] == again.json()["id"]
    assert len(bank.state.requests) == 1
    changed = bank.post("/api/bank/requests", bank.member, {**body, "quantity": 3}, key={"Idempotency-Key": "same"})
    assert (changed.status_code, changed.json()["error"]["code"]) == (409, "idempotency_conflict")


def test_one_members_key_never_replays_anothers_answer(bank: Bank) -> None:
    body = {"sourceId": bank.source_id(), "itemId": 22832, "quantity": 1, "character": "Frogmage"}
    mine = bank.post("/api/bank/requests", bank.member, body, key={"Idempotency-Key": "shared"}).json()
    theirs = bank.post("/api/bank/requests", bank.officer, body, key={"Idempotency-Key": "shared"}).json()
    assert mine["id"] != theirs["id"]
    assert theirs["memberId"] == str(bank.officer_user.user_id)


def test_insufficient_stock_offers_the_waitlist(bank: Bank) -> None:
    r = bank.request(bank.member, quantity=500)
    assert r.status_code == 409
    error = r.json()["error"]
    assert (error["code"], error["details"]) == ("insufficient_stock", {"available": 40, "canWaitlist": True})
    assert r.json()["detail"] == error["message"]
    waitlisted = bank.request(bank.member, quantity=500, waitlist=True)
    assert (waitlisted.status_code, waitlisted.json()["status"]) == (201, "waitlisted")


def test_a_stale_source_blocks_reservations(bank: Bank) -> None:
    bank.hub.pass_time(80 * 3600)
    r = bank.request(bank.member)
    assert (r.status_code, r.json()["error"]["code"]) == (423, "source_stale")
    [source] = bank.get("/api/bank/sources", bank.member).json()
    assert source["freshness"] == "stale"


def test_members_cancel_their_requests_and_stale_revisions_show_the_current_state(bank: Bank) -> None:
    created = bank.request(bank.member).json()
    path = f"/api/bank/requests/{created['id']}/cancel"
    stale = bank.post(path, bank.member, {"expectedRevision": 0})
    assert stale.status_code == 409
    assert stale.json()["error"]["current"]["revision"] == created["revision"]
    cancelled = bank.post(path, bank.member, {"expectedRevision": created["revision"]})
    assert cancelled.json()["status"] == "cancelled"
    other = bank.request(bank.member).json()
    r = bank.post(f"/api/bank/requests/{other['id']}/cancel", bank.admin, {"expectedRevision": other["revision"]})
    assert r.status_code == 200  # an admin may cancel anyone's
    stranger = bank.hub.login(bank.hub.user(("sun", "raider")))
    mine = bank.request(bank.member).json()
    r = bank.post(f"/api/bank/requests/{mine['id']}/cancel", stranger, {"expectedRevision": mine["revision"]})
    assert (r.status_code, r.json()["error"]["code"]) == (403, "forbidden")


def test_ids_in_paths_keep_to_a_safe_alphabet(bank: Bank) -> None:
    assert bank.get("/api/bank/sources/src.1/replica", bank.member).status_code == 422
    assert bank.get("/api/bank/inventory", bank.member, sourceId="../x").status_code == 422


# ----------------------------------------------------------------- officers


def test_an_officer_imports_a_pasted_export_in_several_goes(bank: Bank) -> None:
    snapshot = sample_snapshot(int(bank.hub.now) - 60, "spineshatter-bankalt-test-0002")
    snapshot["tabs"][0]["slots"] *= 30  # big enough to need several parts
    parts = encode_parts(snapshot)
    assert len(parts) > 2
    base = "/api/days/wed/bank/imports"
    opened = bank.post(base, bank.officer)
    assert opened.status_code == 201, opened.text
    import_id = opened.json()["id"]
    first = bank.post(f"{base}/{import_id}/parts", bank.officer, {"text": "```\n" + parts[0] + "\n```"}).json()
    assert (first["received"], first["complete"]) == ([1], False)
    early = bank.get(f"{base}/{import_id}/preview", bank.officer)
    assert (early.status_code, early.json()["error"]["code"]) == (422, "incomplete")
    rest = bank.post(f"{base}/{import_id}/parts", bank.officer, {"text": "\n\n".join(reversed(parts[1:]))}).json()
    assert rest["complete"] and rest["missing"] == []
    preview = bank.get(f"{base}/{import_id}/preview", bank.officer).json()
    assert preview["matchedSource"]["name"] == "Toads main bank"
    assert preview["warnings"] == ["tab 3 was not readable"]
    receipt = bank.post(f"{base}/{import_id}/accept", bank.officer).json()
    assert (receipt["tabsUpdated"], receipt["tabsNotRead"], receipt["duplicate"]) == ([1, 2], [3], False)
    assert [e["type"] for e in bank.state.events] == ["snapshot.accepted"]


def test_a_bad_paste_is_refused_with_the_transport_code(bank: Bank) -> None:
    import_id = bank.post("/api/days/wed/bank/imports", bank.officer).json()["id"]
    r = bank.post(f"/api/days/wed/bank/imports/{import_id}/parts", bank.officer, {"text": "TOADSBANK/2 export=x"})
    assert r.status_code == 422
    assert r.json()["error"] == {
        "code": "transport_error",
        "message": "The pasted text is not a readable export (bad_header)",
        "details": {"code": "bad_header"},
    }


def test_officers_work_the_queue(bank: Bank) -> None:
    created = bank.request(bank.member).json()
    [queued] = bank.get("/api/days/wed/bank/requests", bank.officer).json()
    assert queued["id"] == created["id"]
    base = f"/api/days/wed/bank/requests/{created['id']}"
    approved = bank.post(f"{base}/approve", bank.officer, {"expectedRevision": 1, "note": "ok"}).json()
    assert (approved["status"], approved["managerNote"]) == ("approved", "ok")
    stale = bank.post(f"{base}/deliveries", bank.officer, {"expectedRevision": 1, "quantity": 2})
    assert stale.json()["error"]["code"] == "stale_revision"
    part = bank.post(f"{base}/deliveries", bank.officer, {"expectedRevision": 2, "quantity": 2}).json()
    assert (part["delivered"], part["outstanding"]) == (2, 3)
    [mana] = bank.get("/api/bank/inventory", bank.member, q="Super Mana").json()["items"]
    assert (mana["pendingOutgoing"], mana["directReserved"], mana["available"]) == (2, 3, 35)
    everything = bank.get("/api/days/wed/bank/requests", bank.officer, scope="all").json()
    assert [r["status"] for r in everything] == ["approved"]
    rejected = bank.request(bank.member).json()
    r = bank.post(f"/api/days/wed/bank/requests/{rejected['id']}/reject", bank.officer, {"expectedRevision": 1})
    assert r.json()["status"] == "rejected"


def test_officer_routes_stay_on_the_officers_own_day(bank: Bank) -> None:
    assert bank.post("/api/days/sun/bank/imports", bank.officer).status_code == 403
    assert bank.post("/api/days/wed/bank/imports", bank.member).status_code == 403
    assert bank.post("/api/days/sun/bank/imports", bank.admin).status_code == 201


def test_only_the_global_tier_registers_sources(bank: Bank) -> None:
    body = {"name": "Alt bank", "guild": "Toads Alts", "realm": "Spineshatter", "region": "EU", "managers": ["1"]}
    assert bank.post("/api/admin/bank/sources", bank.officer, body).status_code == 403
    created = bank.post("/api/admin/bank/sources", bank.admin, body)
    assert created.status_code == 201, created.text
    source = created.json()
    patched = bank.hub.client.patch(
        f"/api/admin/bank/sources/{source['id']}",
        headers={**bank.hub.as_(bank.admin), **bank.key()},
        json={"expectedRevision": source["revision"], "audience": "officers"},
    )
    assert patched.json()["audience"] == "officers"
    # An officers-only bank is hidden from plain members (TB-GM-04).
    assert [s["name"] for s in bank.get("/api/bank/sources", bank.member).json()] == ["Toads main bank"]


# ------------------------------------------------------------- the adapter


def test_the_hub_names_the_member_and_their_standing() -> None:
    who = identity_of(Principal(member_id=1, global_officer=True, display_name="Höps", discord_user_id=42))
    assert who == BankIdentity(42, "Höps", ("member", "officer", "admin"))
    headers = who.headers()
    assert headers["X-Toads-Name"] == "H%C3%B6ps" and unquote(headers["X-Toads-Name"]) == "Höps"
    day_officer = identity_of(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}, discord_user_id=7))
    assert day_officer.roles == ("member", "officer")
    assert identity_of(Principal(member_id=1, discord_user_id=7)).roles == ("member",)
    with pytest.raises(BankError) as info:
        identity_of(Principal(member_id=1))
    assert info.value.status == 403


def test_derived_keys_bind_the_member_and_route() -> None:
    request: Any = SimpleNamespace(method="POST", url=SimpleNamespace(path="/api/bank/requests"))
    a = derive_key(BankIdentity(1, "a"), request, "k")
    b = derive_key(BankIdentity(2, "b"), request, "k")
    assert a != b and len(a) == 64


def _client(handler: Any) -> BankClient:
    return BankClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)), BANK_URL, SecretStr(TOKEN))


@pytest.mark.anyio
async def test_the_client_sends_the_token_identity_and_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    await _client(handler).create_request(BankIdentity(42, "Höps", ("member",)), {"a": 1}, "key-1")
    [request] = seen
    assert str(request.url) == f"{BANK_URL}/v1/requests"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert (request.headers["X-Toads-Member"], request.headers["X-Toads-Roles"]) == ("42", "member")
    assert request.headers["Idempotency-Key"] == "key-1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("answer", "status", "code"),
    [
        (httpx.Response(401, json={"error": {"code": "unauthorised", "message": "no"}}), 502, "bank_unavailable"),
        (httpx.Response(500, text="boom"), 502, "bank_unavailable"),
        (httpx.Response(404, text="not json"), 404, "bank_error"),
        (httpx.Response(409, json={"error": "odd"}), 409, "bank_error"),
        (httpx.Response(200, text="not json"), 502, "bank_unavailable"),
    ],
)
async def test_bank_answers_map_to_hub_errors(answer: httpx.Response, status: int, code: str) -> None:
    with pytest.raises(BankError) as info:
        await _client(lambda _r: answer).sources(BankIdentity(1, "a"))
    assert (info.value.status, info.value.code) == (status, code)


@pytest.mark.anyio
async def test_an_unreachable_bank_is_a_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(BankError) as info:
        await _client(handler).inventory(BankIdentity(1, "a"), q="x")
    assert (info.value.status, info.value.code) == (502, "bank_unavailable")


def test_without_configuration_the_bank_says_so(hub: Hub) -> None:
    session = hub.login(hub.user(("wed", "raider")))
    r = hub.get("/api/bank/sources", session)
    assert (r.status_code, r.json()["error"]["code"]) == (503, "bank_not_configured")
    assert hub.get("/api/bank/me", session).json()["configured"] is False


# ------------------------------------------------------------ acting member


def _acting(bank: Bank, user: FakeUser | int | str, token: str = HUB_TOKEN) -> dict[str, str]:
    member = str(user.user_id if isinstance(user, FakeUser) else user)
    return {"Authorization": f"Bearer {token}", "X-Toads-Acting-Member": member}


def test_the_bot_acts_as_a_member_with_that_members_own_roles(bank: Bank) -> None:
    officer = _acting(bank, bank.officer_user)
    me = bank.hub.client.get("/api/bank/me", headers=officer).json()
    assert me["officer_days"] == ["wed"]
    opened = bank.hub.client.post("/api/days/wed/bank/imports", headers={**officer, "Idempotency-Key": "a"})
    assert opened.status_code == 201
    member = _acting(bank, bank.member_user)
    r = bank.hub.client.post("/api/days/wed/bank/imports", headers={**member, "Idempotency-Key": "b"})
    assert r.status_code == 403


@pytest.mark.parametrize(
    ("path", "who", "token", "status"),
    [
        ("/api/bank/me", "member", "wrong", 401),
        ("/api/me", "member", HUB_TOKEN, 401),  # the acting header opens the bank's routes only
        ("/api/bank/me", "abc", HUB_TOKEN, 400),
        ("/api/bank/me", "999999", HUB_TOKEN, 403),  # not in the server
        ("/api/bank/me", "gone", HUB_TOKEN, 403),
    ],
)
def test_acting_member_calls_are_refused_when_they_should_be(
    bank: Bank, path: str, who: str, token: str, status: int
) -> None:
    gone = bank.hub.user(in_guild=False)
    member: Any = {"member": bank.member_user, "gone": gone}.get(who, who)
    assert bank.hub.client.get(path, headers=_acting(bank, member, token)).status_code == status


def test_discord_being_down_is_a_503_for_acting_calls(bank: Bank) -> None:
    async def down(_user_id: int) -> None:
        from toads_api.discord_api import DiscordError

        raise DiscordError("down")

    bank.hub.services.discord.guild_member = down  # type: ignore[method-assign]
    r = bank.hub.client.get("/api/bank/me", headers=_acting(bank, bank.member_user))
    assert r.status_code == 503


# ------------------------------------------------------------------ events

BANK_MANIFEST = BotManifest(name=BOT, actions=[DM, POST])


def _request(**extra: Any) -> dict[str, Any]:
    return {
        "id": "req_1",
        "revision": 2,
        "status": "reserved",
        "memberId": "5678",
        "memberName": "Frog_ger @everyone",
        "character": "Frogmage",
        "itemName": "Super *Mana* Potion",
        "quantity": 5,
        "delivered": 0,
        "outstanding": 5,
        "note": "for Kara",
        "managers": ["1234", "5555"],
        **extra,
    }


def _event(event_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": event_id, "type": kind, "occurredAt": 1790800000, "payload": payload}


def _send_event(bank: Bank, body: dict[str, Any], token: str = TOKEN) -> httpx.Response:
    return bank.hub.client.post("/api/bank/events", json=body, headers={"Authorization": f"Bearer {token}"})


def test_events_need_the_banks_token(bank: Bank) -> None:
    assert _send_event(bank, _event("e1", "request.created", {}), token=HUB_TOKEN).status_code == 401
    assert _send_event(bank, _event("e1", "request.created", {}), token="").status_code == 401


def test_an_assigned_request_dms_each_manager_once(bank: Bank) -> None:
    body = _event("evt_1", "request.assigned", {"request": _request(), "managers": ["1234", "5555", "not-an-id"]})
    first = _send_event(bank, body)
    assert first.json() == {"accepted": True, "duplicate": False, "actions": 2}
    assert _send_event(bank, body).json()["duplicate"] is True
    actions = bank.hub.services.bots.pending(BOT)
    assert [(a.kind, a.payload["user_id"]) for a in actions] == [(DM, "1234"), (DM, "5555")]
    assert actions[0].payload["manage"] == {"request_id": "req_1", "revision": 2}
    content = actions[0].payload["content"]
    assert "Super \\*Mana\\* Potion" in content and "Frog\\_ger \\@everyone" in content


def test_an_updated_request_dms_the_requester(bank: Bank) -> None:
    payload = {"request": _request(status="approved", managerNote="see you <@1>"), "change": "approved"}
    _send_event(bank, _event("evt_2", "request.updated", payload))
    [action] = bank.hub.services.bots.pending(BOT)
    assert action.payload["user_id"] == "5678" and "manage" not in action.payload
    assert "was approved" in action.payload["content"] and "\\<\\@1\\>" in action.payload["content"]


def _events(bank: Bank, **channels: Any) -> BankEvents:
    bank.hub.services.bank_events = BankEvents(bank.hub.services.bots, **channels)
    return bank.hub.services.bank_events


def test_an_accepted_snapshot_is_posted_to_its_days_channel_or_the_bank_channel(bank: Bank) -> None:
    _events(bank, bank_channel=300, day_channels={"wed": 301})
    receipt = {"tabsUpdated": [1, 2], "tabsNotRead": [3], "tabsKeptAsHistory": [4]}
    for n, day in enumerate(("wed", None)):
        source = {"name": "Toads [main] bank", "raidDay": day}
        _send_event(bank, _event(f"snap_{n}", "snapshot.accepted", {"source": source, "receipt": receipt}))
    posts = bank.hub.services.bots.pending(BOT)
    assert [p.payload["channel_id"] for p in posts] == ["301", "300"]
    assert "Toads \\[main\\] bank" in posts[0].payload["content"]
    assert "Not read" in posts[0].payload["content"] and "history: 4" in posts[0].payload["content"]


def test_without_a_bank_channel_snapshots_are_not_posted(bank: Bank) -> None:
    r = _send_event(bank, _event("snap", "snapshot.accepted", {"source": {"name": "x"}, "receipt": {}}))
    assert r.json()["actions"] == 0


def test_a_dm_that_finally_fails_goes_to_the_fallback_channel(bank: Bank) -> None:
    _events(bank, bank_channel=300, fallback_channel=302)
    bots = bank.hub.services.bots
    _send_event(bank, _event("evt_3", "request.assigned", {"request": _request(managers=["1234"])}))
    [dm] = bots.pending(BOT)
    for _ in range(5):
        bots.complete(BOT, dm.id, ActionResult(ok=False, error="Forbidden: cannot DM"))
    [fallback] = bots.pending(BOT)
    assert (fallback.kind, fallback.payload["channel_id"]) == (POST, "302")
    assert "could not be reached by DM about request req\\_1" in fallback.payload["content"]


def test_a_delivered_dm_needs_no_fallback(bank: Bank) -> None:
    _events(bank, fallback_channel=302)
    bots = bank.hub.services.bots
    _send_event(bank, _event("evt_4", "request.assigned", {"request": _request(managers=["1234"])}))
    [dm] = bots.pending(BOT)
    bots.complete(BOT, dm.id, ActionResult(refs={"message_id": 1}))
    assert bots.pending(BOT) == []


def test_an_event_the_hub_cannot_act_on_is_retried(bank: Bank) -> None:
    bots = bank.hub.services.bots
    bots.register(BotManifest(name=BOT, actions=[POST]))  # an old bank bot that cannot DM yet
    body = _event("evt_5", "request.updated", {"request": _request(), "change": "rejected"})
    assert _send_event(bank, body).status_code == 503
    bots.register(BANK_MANIFEST)
    assert _send_event(bank, body).json() == {"accepted": True, "duplicate": False, "actions": 1}


def test_events_the_hub_does_not_act_on_are_acknowledged(bank: Bank) -> None:
    assert _send_event(bank, _event("evt_6", "request.created", {"request": _request()})).json()["actions"] == 0
    assert BankEvents(bank.hub.services.bots).handle(BankEvent(id="x", type="request.updated")) == []


@pytest.mark.security
def test_bot_messages_escape_names_and_mention_syntax() -> None:
    assert messages.escape("@everyone **hi** <@123>") == "\\@everyone \\*\\*hi\\*\\* \\<\\@123\\>"
    assert messages.escape("line\nbreak " + "x" * 100) == "line break " + "x" * 53
    text = messages.updated(_request(delivered=2, outstanding=3), "delivered")
    assert "had a delivery recorded" in text and "Delivered 2, still to come 3" in text
    assert "changed (" in messages.updated(_request(), "teleported")
    assert len(messages.assigned(_request(note="n" * 5000))) <= messages.MESSAGE_LIMIT
    assert messages.snapshot_accepted({"name": "x"}, {}, None).startswith(
        "Bank snapshot accepted for **x**, uploaded by someone"
    )
