"""The site's half of the two-way bot bridge: BotBridge's rules and the /api/bots routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from toads_api.bots.bridge import MAX_ATTEMPTS, BotBridge, BridgeError, InMemoryBridgeStore
from toads_api.bots.models import ActionResult, BotManifest, DiscordEvent, SiteAction

from conftest import Hub

BOT = {"Authorization": "Bearer test-service-token"}
RELAY = BotManifest(name="relay", description="test", actions=["say"], events=["message"])


def _bridge() -> BotBridge:
    bridge = BotBridge(InMemoryBridgeStore(), clock=lambda: 1_000_000.0)
    bridge.register(RELAY)
    return bridge


def _event(event_id: str = "message:1", kind: str = "message") -> DiscordEvent:
    return DiscordEvent(
        event_id=event_id, kind=kind, occurred_at=datetime(2026, 9, 28, tzinfo=UTC), channel_id=111, user_id=7
    )


# ---------------------------------------------------------------------- rules


def test_site_actions_queue_for_their_bot_in_order() -> None:
    bridge = _bridge()
    first = bridge.send("relay", "say", {"channel_id": 111, "text": "hi"})
    second = bridge.send("relay", "say", {"channel_id": 111, "text": "again"})
    bridge.send("other", "anything")  # an unregistered bot still gets its actions once it starts
    assert [a.id for a in bridge.pending("relay")] == [first.id, second.id]
    assert [a.kind for a in bridge.pending("other")] == ["anything"]


def test_a_registered_bot_only_gets_actions_it_declared() -> None:
    with pytest.raises(BridgeError) as info:
        _bridge().send("relay", "ban_everyone")
    assert info.value.status == 422


def test_a_result_finishes_the_action_and_reaches_listeners() -> None:
    bridge = _bridge()
    seen: list[tuple[int, dict[str, Any]]] = []

    @bridge.on_result("relay", "say")
    def remember(action: SiteAction, result: ActionResult) -> None:
        seen.append((action.id, dict(result.refs)))

    action = bridge.send("relay", "say", {"channel_id": 111, "text": "hi"})
    bridge.complete("relay", action.id, ActionResult(refs={"message_id": 42}))
    assert bridge.pending("relay") == []
    assert seen == [(action.id, {"message_id": 42})]


def test_failed_actions_are_retried_then_given_up() -> None:
    bridge = _bridge()
    action = bridge.send("relay", "say")
    for attempt in range(1, MAX_ATTEMPTS):
        bridge.complete("relay", action.id, ActionResult(ok=False, error="boom"))
        assert [a.attempts for a in bridge.pending("relay")] == [attempt]
    bridge.complete("relay", action.id, ActionResult(ok=False, error="boom"))
    assert bridge.pending("relay") == []


def test_a_bot_cannot_answer_another_bots_action() -> None:
    bridge = _bridge()
    action = bridge.send("relay", "say")
    with pytest.raises(BridgeError) as info:
        bridge.complete("other", action.id, ActionResult())
    assert info.value.status == 404


def test_events_reach_their_listeners_once() -> None:
    bridge = _bridge()
    got: list[str] = []

    @bridge.on_event("relay", "message", name="log")
    def log(bot: str, event: DiscordEvent) -> None:
        got.append(f"{bot}/{event.event_id}")

    receipt = bridge.receive("relay", _event())
    assert (receipt.accepted, receipt.duplicate, receipt.handled_by) == (True, False, ["log"])
    assert bridge.receive("relay", _event()).duplicate
    assert got == ["relay/message:1"]


@pytest.mark.parametrize(("bot", "kind", "status"), [("ghost", "message", 409), ("relay", "reaction", 422)])
def test_events_from_unknown_bots_or_undeclared_kinds_are_refused(bot: str, kind: str, status: int) -> None:
    with pytest.raises(BridgeError) as info:
        _bridge().receive(bot, _event(kind=kind))
    assert info.value.status == status


# --------------------------------------------------------------------- routes


def test_routes_need_the_service_token(hub: Hub) -> None:
    assert hub.client.get("/api/bots").status_code == 401
    assert hub.client.get("/api/bots", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_a_bot_round_trip_over_http(hub: Hub) -> None:
    c = hub.client
    assert c.put("/api/bots/relay", headers=BOT, json=RELAY.model_dump()).status_code == 200
    assert [b["name"] for b in c.get("/api/bots", headers=BOT).json()] == ["relay"]

    bridge = hub.services.bots
    heard: list[str] = []
    bridge.on_event("relay", "message", name="test")(lambda _bot, e: heard.append(str(e.payload["content"])))

    action = bridge.send("relay", "say", {"channel_id": 111, "text": "hello"})
    pulled = c.get("/api/bots/relay/actions", headers=BOT).json()
    assert [(a["id"], a["kind"], a["payload"]["text"]) for a in pulled] == [(action.id, "say", "hello")]
    r = c.post(f"/api/bots/relay/actions/{action.id}/result", headers=BOT, json={"refs": {"message_id": 9}})
    assert r.status_code == 204
    assert c.get("/api/bots/relay/actions", headers=BOT).json() == []

    event = _event().model_dump(mode="json") | {"payload": {"content": "from Discord"}}
    r = c.post("/api/bots/relay/events", headers=BOT, json=event)
    assert r.status_code == 202
    assert r.json() == {"accepted": True, "duplicate": False, "handled_by": ["test"]}
    assert heard == ["from Discord"]


@pytest.mark.parametrize(
    ("method", "path", "body", "status"),
    [
        ("PUT", "/api/bots/relay", {"name": "other"}, 422),
        ("PUT", "/api/bots/Not A Name", {"name": "Not A Name"}, 422),
        ("POST", "/api/bots/relay/actions/999/result", {}, 404),
        (
            "POST",
            "/api/bots/ghost/events",
            {"event_id": "x", "kind": "message", "occurred_at": "2026-09-28T00:00:00Z"},
            409,
        ),
    ],
)
def test_bad_requests(hub: Hub, method: str, path: str, body: dict[str, Any], status: int) -> None:
    assert hub.client.request(method, path, headers=BOT, json=body).status_code == status
