"""The bank binding (docs/bank.md): site actions, slash commands and buttons, with Discord and the hub faked."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import httpx
import pytest
from pydantic import SecretStr
from toads_bot.kit import ActionResult, ActionRunner, BotContext, OpenGate, SiteAction
from toads_bot.kit import bank as b
from toads_bot.kit.bank import NO_PINGS, Bank, DeliveryModal, ImportModal
from toads_bot.kit.bank_api import ACTING_MEMBER, BankApiError, HttpBankApi
from toads_bot.kit.specs import BANK, SPECS

GUILD, CHANNEL, OFFICER, MEMBER = 1, 111, 1001, 2002


def run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeApi:
    """The hub's bank routes in memory. `fail` maps a method name to the errors its next calls raise."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.fail: dict[str, list[BankApiError]] = {}
        self.officer_days = {OFFICER: ["wed"]}
        self.parts_result: dict[str, Any] = {"received": [1], "total": 2, "missing": [2], "complete": False}
        self.items: list[dict[str, Any]] = []
        self.opened = 0

    def _record(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))
        errors = self.fail.get(name)
        if errors:
            raise errors.pop(0)

    def named(self, name: str) -> list[tuple[Any, ...]]:
        return [args for n, args in self.calls if n == name]

    async def me(self, member: int) -> dict[str, Any]:
        self._record("me", member)
        return {"officer_days": self.officer_days.get(member, [])}

    async def open_import(self, member: int, day: str, key: str) -> dict[str, Any]:
        self._record("open_import", member, day, key)
        self.opened += 1
        return {"id": f"imp_{self.opened}"}

    async def add_parts(self, member: int, day: str, import_id: str, text: str, key: str) -> dict[str, Any]:
        self._record("add_parts", member, day, import_id, text, key)
        return self.parts_result

    async def preview(self, member: int, day: str, import_id: str) -> dict[str, Any]:
        self._record("preview", member, day, import_id)
        return {
            "matchedSource": {"id": "src_1", "name": "Toads *main* bank"},
            "source": {"guild": "Toads", "realm": "Spineshatter", "region": "EU"},
            "uploader": {"name": "Bankalt"},
            "capturedAt": 1790799000,
            "tabs": [
                {"index": 1, "name": "Potions", "status": "observed", "occupied": 40, "items": 10},
                {"index": 3, "name": "Officers", "status": "unknown", "occupied": 0, "items": 0},
            ],
            "warnings": ["tab 3 was not readable"],
            "existingReceipt": None,
            "stable": False,
        }

    async def accept(self, member: int, day: str, import_id: str, key: str) -> dict[str, Any]:
        self._record("accept", member, day, import_id, key)
        return {"tabsUpdated": [1, 2], "tabsNotRead": [3], "duplicate": False}

    async def inventory(self, member: int, q: str) -> dict[str, Any]:
        self._record("inventory", member, q)
        return {"items": self.items}

    async def create_request(self, member: int, body: dict[str, Any], key: str) -> dict[str, Any]:
        self._record("create_request", member, body, key)
        status = "waitlisted" if body.get("waitlist") else "reserved"
        return {"id": "req_1", "itemName": "Super Mana Potion", "status": status, **body}

    async def manage(
        self, member: int, day: str, request_id: str, action: str, body: dict[str, Any], key: str
    ) -> dict[str, Any]:
        self._record("manage", member, day, request_id, action, body, key)
        return {
            "id": request_id,
            "itemName": "Super Mana Potion",
            "quantity": 5,
            "character": "Frogmage",
            "status": "approved",
        }


def ctx() -> BotContext:
    return BotContext(
        manifest=BANK.manifest(), guild_id=GUILD, link=MagicMock(), gate=OpenGate(), channel_ids=frozenset({CHANNEL})
    )


def binding(api: FakeApi | None = None, bot: Any = None) -> Bank:
    return Bank(bot or MagicMock(), ctx(), api=api or FakeApi())


def interaction(user: int = OFFICER, interaction_id: int = 9000, custom_id: str | None = None) -> Any:
    return SimpleNamespace(
        id=interaction_id,
        user=SimpleNamespace(id=user),
        type=discord.InteractionType.component if custom_id else discord.InteractionType.application_command,
        data={"custom_id": custom_id} if custom_id else {},
        response=SimpleNamespace(defer=AsyncMock(), send_modal=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def replied(i: Any) -> tuple[str, dict[str, Any]]:
    """The last ephemeral follow-up: its text and keyword arguments."""
    call = i.followup.send.await_args
    assert call.kwargs["ephemeral"] is True and call.kwargs["allowed_mentions"] is NO_PINGS
    return call.args[0], call.kwargs


def custom_ids(view: discord.ui.View) -> list[str]:
    return [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]


def action(kind: str, **payload: Any) -> SiteAction:
    return SiteAction(id=1, bot="bank", kind=kind, payload=payload, created_at=datetime(2026, 10, 1, tzinfo=UTC))


# ------------------------------------------------------------------- spec


def test_the_bank_bot_carries_out_dms_and_posts() -> None:
    assert SPECS["bank"] is BANK
    manifest = BANK.manifest()
    assert (manifest.actions, manifest.events) == (["bank.dm", "bank.post"], [])


# ----------------------------------------------------------- site actions


def test_a_manager_dm_carries_buttons_with_the_request_and_revision() -> None:
    user = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(id=77)))
    bot = MagicMock()
    bot.fetch_user = AsyncMock(return_value=user)
    link = MagicMock()
    link.register = AsyncMock()
    link.pull = AsyncMock(
        return_value=[
            action("bank.dm", user_id="1234", content="@everyone hi", manage={"request_id": "req_1", "revision": 2})
        ]
    )
    link.report = AsyncMock()

    async def go() -> list[str]:
        bank = binding(bot=bot)
        await ActionRunner(BANK.manifest(), link, bank.handlers()).run_once()
        return custom_ids(user.send.await_args.kwargs["view"])

    ids = run(go())
    bot.fetch_user.assert_awaited_once_with(1234)
    assert user.send.await_args.args == ("@everyone hi",)
    assert user.send.await_args.kwargs["allowed_mentions"] is NO_PINGS
    assert ids == ["bank:approve:req_1:2", "bank:reject:req_1:2", "bank:deliver:req_1:2"]
    link.report.assert_awaited_once_with("bank", 1, ActionResult(refs={"message_id": 77}))


def test_a_plain_dm_has_no_buttons_and_a_closed_dm_fails_the_action() -> None:
    user = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(id=5)))
    bot = MagicMock()
    bot.fetch_user = AsyncMock(return_value=user)
    run(binding(bot=bot).dm(action("bank.dm", user_id="5678", content="Your request was approved.")))
    assert "view" not in user.send.await_args.kwargs
    user.send = AsyncMock(side_effect=RuntimeError("Cannot send messages to this user"))
    with pytest.raises(RuntimeError):
        run(binding(bot=bot).dm(action("bank.dm", user_id="5678", content="x")))


def test_posts_go_only_to_the_bots_channels_without_pings() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=SimpleNamespace(id=555))
    bot = MagicMock()
    bot.get_channel.return_value = channel
    refs = run(binding(bot=bot).post(action("bank.post", channel_id=str(CHANNEL), content="Snapshot accepted")))
    assert refs == {"channel_id": CHANNEL, "message_id": 555}
    channel.send.assert_awaited_once_with("Snapshot accepted", allowed_mentions=NO_PINGS)
    with pytest.raises(LookupError):
        run(binding(bot=bot).post(action("bank.post", channel_id="999", content="x")))


# ---------------------------------------------------------------- imports


def test_import_opens_a_modal_of_five_paragraph_boxes() -> None:
    i = interaction()

    async def go() -> ImportModal:
        await binding().open_import_modal(i)
        return i.response.send_modal.await_args.args[0]

    modal = run(go())
    assert len(modal.boxes) == 5
    assert all(box.style is discord.TextStyle.paragraph and box.max_length == 4000 for box in modal.boxes)
    assert [box.required for box in modal.boxes] == [True, False, False, False, False]


def test_a_partial_paste_reports_received_and_missing_parts() -> None:
    api = FakeApi()
    bank = binding(api)
    i = interaction()
    run(bank.import_text(i, "TOADSBANK/1 export=... part=1/2"))
    i.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    assert replied(i)[0] == "Received parts 1 of 2. Still missing: 2."
    assert bank.imports == {OFFICER: "imp_1"}
    run(bank.import_text(interaction(interaction_id=9001), "part 2"))
    assert api.opened == 1  # the second paste goes into the same session
    assert [args[2] for args in api.named("add_parts")] == ["imp_1", "imp_1"]


def test_a_complete_paste_shows_the_preview_with_accept_and_cancel() -> None:
    api = FakeApi()
    api.parts_result = {"received": [1, 2], "total": 2, "missing": [], "complete": True}
    i = interaction()
    run(binding(api).import_text(i, "parts"))
    text, kwargs = replied(i)
    assert text.startswith("All 2 parts received.\nSnapshot of **Toads \\*main\\* bank**, captured <t:1790799000:f>")
    assert "Tab 3 Officers (unknown): 0 items in 0 slots" in text
    assert "Warning: tab 3 was not readable" in text and "some counts may be off" in text
    assert custom_ids(kwargs["view"]) == ["bank:accept:imp_1", "bank:discard:imp_1"]


def test_an_expired_import_is_reopened() -> None:
    api = FakeApi()
    bank = binding(api)
    bank.imports[OFFICER] = "imp_old"
    api.fail["add_parts"] = [BankApiError(422, "import_expired", "expired")]
    run(bank.import_text(interaction(), "parts"))
    assert bank.imports[OFFICER] == "imp_1"
    assert [args[2] for args in api.named("add_parts")] == ["imp_old", "imp_1"]


def test_members_without_an_officer_day_cannot_import() -> None:
    i = interaction(user=MEMBER)
    run(binding().import_text(i, "parts"))
    assert replied(i)[0] == "Only officers can import bank snapshots."


def test_a_bad_paste_says_what_was_wrong() -> None:
    api = FakeApi()
    api.fail["add_parts"] = [BankApiError(422, "transport_error", "The pasted text is not a readable export (crc)")]
    i = interaction()
    run(binding(api).import_text(i, "junk"))
    assert replied(i)[0] == "The pasted text is not a readable export \\(crc\\)"


def test_accept_and_cancel_buttons() -> None:
    api = FakeApi()
    bank = binding(api)
    bank.imports[OFFICER] = "imp_1"
    i = interaction(custom_id="bank:accept:imp_1")
    run(bank.on_interaction(i))
    assert replied(i)[0] == "Snapshot accepted. Tabs updated: 1, 2. Not read, kept as they were: 3."
    assert api.named("accept") == [(OFFICER, "wed", "imp_1", "accept:imp_1")]
    assert bank.imports == {}
    bank.imports[OFFICER] = "imp_2"
    i = interaction(custom_id="bank:discard:imp_2")
    run(bank.on_interaction(i))
    i.response.send_message.assert_awaited_once_with("Import cancelled; nothing was saved.", ephemeral=True)
    assert bank.imports == {}


# ------------------------------------------------------------ find, request

MANA = {
    "itemId": 22832,
    "name": "Super Mana Potion",
    "observed": 40,
    "available": 21,
    "sources": [{"sourceId": "src_1", "available": 3}, {"sourceId": "src_2", "available": 18}],
}
MANA_OIL = {"itemId": 20748, "name": "Brilliant Mana Oil", "observed": 2, "available": 2, "sources": []}


def test_find_lists_matching_items() -> None:
    api = FakeApi()
    api.items = [MANA, MANA_OIL]
    i = interaction(user=MEMBER)
    run(binding(api).find(i, "mana"))
    assert replied(i)[0] == (
        "Super Mana Potion: 21 available, 40 in the bank\nBrilliant Mana Oil: 2 available, 2 in the bank"
    )
    i = interaction(user=MEMBER)
    run(binding(FakeApi()).find(i, "@everyone"))
    assert replied(i)[0] == "Nothing in the bank matches \\@everyone."


def test_a_request_takes_the_source_with_the_most_available() -> None:
    api = FakeApi()
    api.items = [MANA, MANA_OIL]
    i = interaction(user=MEMBER, interaction_id=42)
    run(binding(api).request(i, "super mana potion", 5, " Frogmage "))
    [(member, body, key)] = api.named("create_request")
    assert (member, key) == (MEMBER, "request:42")
    assert body == {"sourceId": "src_2", "itemId": 22832, "quantity": 5, "character": "Frogmage"}
    assert replied(i)[0] == "Request req\\_1: 5 x Super Mana Potion for Frogmage is reserved."


def test_insufficient_stock_offers_a_waitlist_button_that_works() -> None:
    api = FakeApi()
    api.items = [MANA]
    api.fail["create_request"] = [
        BankApiError(409, "insufficient_stock", "Not enough", {"available": 18, "canWaitlist": True})
    ]
    bank = binding(api)
    i = interaction(user=MEMBER)
    run(bank.request(i, "Super Mana Potion", 50, "Frogmage"))
    text, kwargs = replied(i)
    assert text == "Not enough in stock: 18 available. Join the waitlist instead?"
    [waitlist] = custom_ids(kwargs["view"])
    assert waitlist == "bank:waitlist:src_2:22832:50:Frogmage"
    press = interaction(user=MEMBER, interaction_id=43, custom_id=waitlist)
    run(bank.on_interaction(press))
    assert api.named("create_request")[-1][1]["waitlist"] is True
    assert replied(press)[0].endswith("is waitlisted.")


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], "Nothing in the bank is called mana."),
        ([MANA, MANA_OIL], "Several items match: Super Mana Potion, Brilliant Mana Oil. Use the full name."),
        ([{**MANA, "name": "Mana", "sources": []}], "No bank you can see holds Mana."),
    ],
)
def test_a_request_needs_one_item_held_somewhere(items: list[dict[str, Any]], expected: str) -> None:
    api = FakeApi()
    api.items = items
    i = interaction(user=MEMBER)
    run(binding(api).request(i, "mana", 1, "Frogmage"))
    assert replied(i)[0] == expected
    assert api.named("create_request") == []


# ------------------------------------------------------------- the queue


def test_approve_carries_the_revision_and_a_stable_key() -> None:
    api = FakeApi()
    i = interaction(custom_id="bank:approve:req_1:2")
    run(binding(api).on_interaction(i))
    assert api.named("manage") == [(OFFICER, "wed", "req_1", "approve", {"expectedRevision": 2}, "approve:req_1:2")]
    assert replied(i)[0] == "Request req\\_1: 5 x Super Mana Potion for Frogmage is approved."


def test_a_stale_button_shows_the_current_state() -> None:
    api = FakeApi()
    current = {
        "id": "req_1",
        "revision": 4,
        "status": "fulfilled",
        "quantity": 5,
        "itemName": "Super Mana Potion",
        "character": "Frogmage",
        "delivered": 5,
    }
    api.fail["manage"] = [BankApiError(409, "stale_revision", "stale", current=current)]
    i = interaction(custom_id="bank:reject:req_1:2")
    run(binding(api).on_interaction(i))
    assert replied(i)[0] == (
        "That request has changed since this message was sent. Now: Request req\\_1: 5 x Super Mana Potion for "
        "Frogmage is fulfilled. (revision 4, delivered 5)"
    )


def test_record_delivery_asks_for_the_quantity() -> None:
    api = FakeApi()
    bank = binding(api)
    i = interaction(custom_id="bank:deliver:req_1:3")
    run(bank.on_interaction(i))
    modal = i.response.send_modal.await_args.args[0]
    assert isinstance(modal, DeliveryModal) and (modal.request_id, modal.revision) == ("req_1", 3)
    bad = interaction()
    run(bank.deliver(bad, "req_1", 3, "lots"))
    bad.response.send_message.assert_awaited_once_with("Give the quantity as a whole number.", ephemeral=True)
    run(bank.deliver(interaction(), "req_1", 3, "2"))
    assert api.named("manage")[-1][3:5] == ("deliveries", {"expectedRevision": 3, "quantity": 2})


def test_members_cannot_work_the_queue_from_discord() -> None:
    api = FakeApi()
    i = interaction(user=MEMBER, custom_id="bank:approve:req_1:2")
    run(binding(api).on_interaction(i))
    assert replied(i)[0] == "Only officers can manage bank requests."
    assert api.named("manage") == []


@pytest.mark.parametrize("custom", [None, "other:approve:1:2", "bank:approve:req_1:x", "bank:nonsense"])
def test_other_interactions_are_left_alone(custom: str | None) -> None:
    api = FakeApi()
    i = interaction(custom_id=custom)
    run(binding(api).on_interaction(i))
    assert api.calls == []
    i.followup.send.assert_not_awaited()


def test_a_hub_error_is_explained() -> None:
    assert b.error_text(BankApiError(403, "forbidden", "no")).startswith("You can't do that.")
    assert b.error_text(BankApiError(423, "source_stale", "old")).startswith("That bank has not been captured")
    assert b.error_text(BankApiError(409, "insufficient_stock", "x", {})) == "Not enough in stock."
    assert b.current_text(None) == "That request has changed since this message was sent."
    assert b.receipt_text({"duplicate": True}) == "That snapshot was already accepted; nothing changed."


@pytest.mark.security
def test_names_from_the_bank_are_escaped() -> None:
    assert b.escape("<@123> **x**") == "\\<\\@123\\> \\*\\*x\\*\\*"
    assert b.combine_fields(["a", " ", "", "b"]) == "a\nb"
    assert b.parse_custom_id("bank:approve:req_1:2") == ("approve", ["req_1", "2"])
    assert b.parse_custom_id("nope") is None
    long_list = {"items": [{"name": f"Item {n}", "available": 1, "observed": 1} for n in range(15)]}
    assert b.inventory_text(long_list, "item").endswith(
        "…and 5 more. Narrow the search or use the bank page on the hub."
    )


# ------------------------------------------------------------------ the link


def test_the_http_api_acts_as_the_member_on_the_hubs_bank_routes() -> None:
    seen: list[tuple[str, str, Any, httpx.Headers]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, body, request.headers))
        if request.url.path.endswith("/approve"):
            return httpx.Response(
                409,
                json={
                    "detail": "stale",
                    "error": {"code": "stale_revision", "message": "stale", "current": {"revision": 3}},
                },
            )
        if request.url.path == "/api/bank/inventory":
            return httpx.Response(503, json={"detail": "The guild bank is not set up"})
        return httpx.Response(200, json={"id": "imp_1", "officer_days": ["wed"]})

    api = HttpBankApi("http://hub/", SecretStr("svc"), transport=httpx.MockTransport(handler))

    async def go() -> list[BankApiError]:
        await api.me(OFFICER)
        await api.open_import(OFFICER, "wed", "open:1")
        await api.add_parts(OFFICER, "wed", "imp_1", "text", "parts:1")
        await api.preview(OFFICER, "wed", "imp_1")
        await api.accept(OFFICER, "wed", "imp_1", "accept:imp_1")
        await api.create_request(MEMBER, {"sourceId": "src_1"}, "request:1")
        errors = []
        for call in (
            api.manage(OFFICER, "wed", "req_1", "approve", {"expectedRevision": 2}, "approve:req_1:2"),
            api.inventory(MEMBER, "mana"),
        ):
            try:
                await call
            except BankApiError as error:
                errors.append(error)
        await api.aclose()
        return errors

    stale, unset = run(go())
    assert [(m, p) for m, p, _, _ in seen] == [
        ("GET", "/api/bank/me"),
        ("POST", "/api/days/wed/bank/imports"),
        ("POST", "/api/days/wed/bank/imports/imp_1/parts"),
        ("GET", "/api/days/wed/bank/imports/imp_1/preview"),
        ("POST", "/api/days/wed/bank/imports/imp_1/accept"),
        ("POST", "/api/bank/requests"),
        ("POST", "/api/days/wed/bank/requests/req_1/approve"),
        ("GET", "/api/bank/inventory"),
    ]
    assert all(h["Authorization"] == "Bearer svc" for *_, h in seen)
    assert seen[0][3][ACTING_MEMBER] == str(OFFICER) and seen[5][3][ACTING_MEMBER] == str(MEMBER)
    assert seen[2][2] == {"text": "text"} and seen[2][3]["Idempotency-Key"] == "parts:1"
    assert (stale.code, stale.current) == ("stale_revision", {"revision": 3})
    assert (unset.status, unset.code, unset.message) == (503, "http_503", "The guild bank is not set up")


def test_an_unreachable_hub_is_an_error_the_member_can_read() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    api = HttpBankApi("http://hub", SecretStr("svc"), transport=httpx.MockTransport(handler))
    with pytest.raises(BankApiError) as info:
        run(api.me(1))
    assert info.value.code == "hub_unreachable"
