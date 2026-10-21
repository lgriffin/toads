"""REQ-HUB-BDESK-*: the bank request desk (docs/bank-desk.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server. The Toad Bot is
played by calls with the hub service token, acting for a member, as `/bankrequest` makes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from hub_db import AuditEntry
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
WEB = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"
scenarios(str(FEATURES / "hub_bankdesk.feature"))

BOT = {"authorization": "Bearer test-service-token"}
FLASK, POTION = "Flask of Relentless Assault", "Super Mana Potion"


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _bot_asks(hub: Hub, user_id: int, item: str, quantity: int) -> httpx.Response:
    headers = {**BOT, "x-toads-acting-member": str(user_id)}
    return hub.client.post("/api/bank-desk/requests", headers=headers, json={"item": item, "quantity": quantity})


def _desk(hub: Hub, sid: str, day: str = "wed") -> list[dict[str, Any]]:
    r = hub.get(f"/api/days/{day}/bank-desk/requests", sid)
    assert r.status_code == 200, r.text
    rows: list[dict[str, Any]] = r.json()
    return rows


def _by_item(hub: Hub, people: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["item"]: r for r in _desk(hub, people["officer"])}


def _answer(hub: Hub, people: dict[str, Any], item: str, verdict: str, message: str) -> httpx.Response:
    request_id = _by_item(hub, people)[item]["id"]
    return hub.post(f"/api/days/wed/bank-desk/requests/{request_id}/{verdict}", people["officer"], {"message": message})


def _dms(hub: Hub) -> list[dict[str, Any]]:
    r = hub.client.get("/api/bot/outbox", headers=BOT)
    assert r.status_code == 200, r.text
    return [item["job"] for item in r.json() if item["job"]["kind"] == "send_dm"]


@given("a Wednesday officer")
def a_day_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer"), nick="Croak"))


@given(parsers.parse('a raider who goes by the nickname "{nick}"'))
def a_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    people["raider_user"] = hub.user(("wed", "raider"), nick=nick)


@given(parsers.parse('the raider has asked for {n:d} "{first}" and {m:d} "{second}"'))
def raider_has_asked(hub: Hub, people: dict[str, Any], n: int, first: str, m: int, second: str) -> None:
    for item, quantity in ((first, n), (second, m)):
        assert _bot_asks(hub, people["raider_user"].user_id, item, quantity).status_code == 201


@when(parsers.parse('the Toad Bot asks for {n:d} "{item}" for the raider'))
def bot_asks(hub: Hub, people: dict[str, Any], n: int, item: str) -> None:
    r = _bot_asks(hub, people["raider_user"].user_id, item, n)
    assert r.status_code == 201, r.text


@when(parsers.parse('the Wednesday officer approves the flasks with "{message}"'))
def approve_flasks(hub: Hub, people: dict[str, Any], message: str) -> None:
    r = _answer(hub, people, FLASK, "approve", message)
    assert r.status_code == 200, r.text


@when(parsers.parse('the Wednesday officer denies the potions with "{message}"'))
def deny_potions(hub: Hub, people: dict[str, Any], message: str) -> None:
    r = _answer(hub, people, POTION, "deny", message)
    assert r.status_code == 200, r.text


@when(parsers.parse('another member asks for {n:d} "{item}" on the site'))
def another_asks(hub: Hub, n: int, item: str) -> None:
    sid = hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    r = hub.post("/api/bank-desk/requests", sid, {"item": item, "quantity": n})
    assert r.status_code == 201, r.text
    assert r.json()["source"] == "site"


@when(parsers.parse("the Toad Bot sends the flasks' DM and fails the potions' with \"{reason}\""))
def bot_sends_dms(hub: Hub, reason: str) -> None:
    for job in _dms(hub):
        body = {"error": reason} if POTION in job["payload"]["content"] else {}
        r = hub.client.post(f"/api/bot/outbox/{job['id']}/ack", headers=BOT, json=body)
        assert r.status_code == 200, r.text


@then(parsers.parse('the request desk shows a pending request from "{name}" for {n:d} "{item}" asked from Discord'))
def desk_shows(hub: Hub, people: dict[str, Any], name: str, n: int, item: str) -> None:
    (row,) = _desk(hub, people["officer"])
    assert (row["requester_name"], row["item"], row["quantity"]) == (name, item, n)
    assert (row["status"], row["source"], row["notice"]) == ("pending", "discord", None)
    assert row["discord_user_id"] == str(people["raider_user"].user_id)


@then("the flasks are approved and the potions denied, both by the Wednesday officer")
def answered(hub: Hub, people: dict[str, Any]) -> None:
    rows = _by_item(hub, people)
    assert (rows[FLASK]["status"], rows[POTION]["status"]) == ("approved", "denied")
    for row in rows.values():
        assert row["decided_by_name"] == "Croak"
        assert row["decided_at"] is not None
        assert row["notice"] == "queued"
    assert rows[FLASK]["officer_message"] == "Grab them from Gail after the raid"


@then("the Toad Bot is asked to DM the raider each answer with its message")
def dms_queued(hub: Hub, people: dict[str, Any]) -> None:
    jobs = _dms(hub)
    assert {j["payload"]["discord_user_id"] for j in jobs} == {str(people["raider_user"].user_id)}
    texts = sorted(j["payload"]["content"] for j in jobs)
    assert len(texts) == 2
    assert any(f"{FLASK} x4 was approved by Croak" in t and "Grab them from Gail" in t for t in texts)
    assert any(f"{POTION} x20 was denied by Croak" in t and "We are short this week" in t for t in texts)


@then(parsers.parse('the audit log records "{first}" and "{second}" for Wednesday'))
def audit_records(hub: Hub, first: str, second: str) -> None:
    with hub.db() as db:
        entries = db.scalars(select(AuditEntry).where(AuditEntry.action.startswith("bank_desk."))).all()
    assert sorted((e.action, e.raid_day_id) for e in entries) == sorted([(first, "wed"), (second, "wed")])


@then("the raider cannot see or answer the request desk")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    raider = hub.login(people["raider_user"])
    assert hub.get("/api/days/wed/bank-desk/requests", raider).status_code == 403
    request_id = _by_item(hub, people)[FLASK]["id"]
    assert hub.post(f"/api/days/wed/bank-desk/requests/{request_id}/approve", raider, {}).status_code == 403
    member_id = people["raider_user"].user_id
    assert hub.get(f"/api/days/wed/bank-desk/members/{member_id}/requests", raider).status_code == 403


@then("the Toad Bot's token cannot answer a request for an officer")
def bot_cannot_answer(hub: Hub, people: dict[str, Any]) -> None:
    officer = hub.user(("wed", "officer"))
    request_id = _by_item(hub, people)[FLASK]["id"]
    r = hub.client.post(
        f"/api/days/wed/bank-desk/requests/{request_id}/approve",
        headers={**BOT, "x-toads-acting-member": str(officer.user_id)},
        json={},
    )
    assert r.status_code == 401, r.text


@then("a Sunday officer sees the same request desk under Sunday")
def sunday_officer_sees(hub: Hub, people: dict[str, Any]) -> None:
    sunday = hub.login(hub.user(("sun", "officer")))
    assert {r["item"] for r in _desk(hub, sunday, "sun")} == {FLASK, POTION}
    assert hub.get("/api/days/wed/bank-desk/requests", sunday).status_code == 403


@then("both requests are still pending")
def still_pending(hub: Hub, people: dict[str, Any]) -> None:
    assert {r["status"] for r in _desk(hub, people["officer"])} == {"pending"}
    assert _dms(hub) == []


@then("the raider's own requests list the potions pending and the flasks approved, newest first")
def own_history(hub: Hub, people: dict[str, Any]) -> None:
    r = hub.get("/api/bank-desk/requests/mine", hub.login(people["raider_user"]))
    assert r.status_code == 200, r.text
    assert [(x["item"], x["status"]) for x in r.json()] == [(POTION, "pending"), (FLASK, "approved")]
    people["mine"] = r.json()


@then("the officer's view of the raider's history lists the same two requests")
def officer_history(hub: Hub, people: dict[str, Any]) -> None:
    member_id = people["raider_user"].user_id
    r = hub.get(f"/api/days/wed/bank-desk/members/{member_id}/requests", people["officer"])
    assert r.status_code == 200, r.text
    assert r.json() == people["mine"]
    assert len(_desk(hub, people["officer"])) == 3


@then("denying the flasks is refused as already answered")
def second_answer_refused(hub: Hub, people: dict[str, Any]) -> None:
    r = _answer(hub, people, FLASK, "deny", "Changed my mind")
    assert r.status_code == 409, r.text
    assert _by_item(hub, people)[FLASK]["status"] == "approved"


@then("the Toad Bot is asked for just one DM")
def one_dm(hub: Hub) -> None:
    assert len(_dms(hub)) == 1


@then(parsers.parse("the request desk shows the flasks' DM sent and the potions' DM failed with \"{reason}\""))
def notices_shown(hub: Hub, people: dict[str, Any], reason: str) -> None:
    rows = _by_item(hub, people)
    assert (rows[FLASK]["notice"], rows[FLASK]["notice_error"]) == ("sent", None)
    assert (rows[POTION]["notice"], rows[POTION]["notice_error"]) == ("failed", reason)
    assert _dms(hub) == []


@given("the officers' held Bank page", target_fixture="notice")
def held_bank_page() -> str:
    return (WEB / "lib" / "components" / "ForeverNotice.svelte").read_text(encoding="utf-8")


@then("it shows the request desk above the Forever preview")
def desk_in_notice(notice: str) -> None:
    desk = notice.index("<BankDesk backend={deskBackend} />")
    assert (
        notice.rindex("{#if preview?.mockup === 'bank'}", 0, desk) < desk < notice.index('aria-labelledby="notice-h"')
    )
    # The Forever preview itself is unchanged: Gail and the mockup stay (test_hub_front.py).
    assert "{#if preview.mockup === 'bank'}<BankCounter /><BankMockup />{/if}" in notice


@given("the Bank page", target_fixture="bank_page")
def bank_page() -> dict[str, str]:
    files = {
        "page": "routes/bank/+page.svelte",
        "live": "lib/components/BankLive.svelte",
        "mine": "lib/bank-mine.ts",
        "redeem": "lib/components/BankRedeem.svelte",
        "desk": "lib/components/BankDesk.svelte",
    }
    return {key: (WEB / path).read_text(encoding="utf-8") for key, path in files.items()}


@then("it asks with one form that sends a stocked item to the bank's stock and anything else to the request desk")
def one_ask_form(bank_page: dict[str, str]) -> None:
    live = bank_page["live"]
    assert live.count("<form") == 1 and "Ask the bank" in live
    assert "let chosen = $derived(stockedItem(inventory.items, itemText));" in live
    assert "askDesk(typed, quantity)" in live and "send({ sourceId, itemId: chosen.itemId" in live


@then("it lists the member's requests from both in one list, newest first")
def one_request_list(bank_page: dict[str, str]) -> None:
    assert "myRequestRows(mine, deskMine," in bank_page["live"]
    assert ".sort((a, b) => b.at - a.at)" in bank_page["mine"]
    assert bank_page["live"].count('<h2 id="mine-h">Your requests</h2>') == 1


@then("the request desk on it shows only officers' answering, not a second ask form or list")
def desk_answers_only(bank_page: dict[str, str]) -> None:
    assert "<BankDesk backend={desk} own={false} />" in bank_page["page"]
    assert "<BankLive {desk} />" in bank_page["page"]
    assert '{#if own}\n    <div class="own">' in bank_page["desk"]


@then("the officer token waits behind a disclosure")
def token_behind_disclosure(bank_page: dict[str, str]) -> None:
    redeem = bank_page["redeem"]
    assert '<details class="card redeem">' in redeem and "Have an officer token?" in redeem
