"""The two-way bot kit: specs and manifests, the action runner, the example relay binding and the HTTP link."""

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
from toads_bot.kit import (
    ActionResult,
    ActionRunner,
    Binding,
    BotContext,
    BotManifest,
    BotSpec,
    DiscordEvent,
    EventReceipt,
    HttpHubLink,
    KitSettings,
    OpenGate,
    SiteAction,
    build_bot,
)
from toads_bot.kit.relay import NO_PINGS, Relay
from toads_bot.kit.specs import RELAY, SPECS

GUILD, CHANNEL = 1, 111


def run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeLink:
    """A hub in memory: queued actions out, reported results and received events in."""

    def __init__(self, actions: list[SiteAction] | None = None) -> None:
        self.actions = actions or []
        self.manifests: list[BotManifest] = []
        self.results: dict[int, ActionResult] = {}
        self.events: list[DiscordEvent] = []

    async def register(self, manifest: BotManifest) -> None:
        self.manifests.append(manifest)

    async def pull(self, bot: str) -> list[SiteAction]:
        return [a for a in self.actions if a.bot == bot and a.id not in self.results]

    async def report(self, bot: str, action_id: int, result: ActionResult) -> None:
        self.results[action_id] = result

    async def send_event(self, bot: str, event: DiscordEvent) -> EventReceipt:
        self.events.append(event)
        return EventReceipt(accepted=True, handled_by=["test"])


def action(kind: str = "say", action_id: int = 1, **payload: Any) -> SiteAction:
    return SiteAction(
        id=action_id, bot="relay", kind=kind, payload=payload, created_at=datetime(2026, 9, 28, tzinfo=UTC)
    )


def ctx(link: FakeLink) -> BotContext:
    return BotContext(name="relay", guild_id=GUILD, link=link, gate=OpenGate(), channel_ids=frozenset({CHANNEL}))


def settings(monkeypatch: pytest.MonkeyPatch, **extra: str) -> KitSettings:
    env = {
        "TOADS_DISCORD_BOT_TOKEN": "planted-token",
        "TOADS_DISCORD_GUILD_ID": str(GUILD),
        "TOADS_HUB_API_URL": "http://api:8000",
        "TOADS_HUB_SERVICE_TOKEN": "svc",
        **extra,
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return KitSettings()


# ---------------------------------------------------------------- specs


def test_the_manifest_lists_every_bindings_actions_and_events() -> None:
    assert RELAY.manifest() == BotManifest(
        name="relay", description=RELAY.description, actions=["say"], events=["message"]
    )
    assert SPECS["relay"] is RELAY


def test_two_bindings_cannot_claim_the_same_action() -> None:
    class Echo(Binding):
        site_actions = {"say": "say"}  # noqa: RUF012

    with pytest.raises(ValueError, match="same action kind"):
        BotSpec(name="clash", description="", bindings=(Relay, Echo)).manifest()


@pytest.mark.security
def test_token_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    assert "planted-token" not in repr(settings(monkeypatch))


def test_a_spec_builds_a_bot_without_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = build_bot(RELAY, settings(monkeypatch, TOADS_BOT_CHANNEL_IDS="[111]"), link=FakeLink())
    assert bot.intents.message_content
    assert not bot.intents.members


def test_the_cli_refuses_an_unknown_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    from toads_bot.kit import cli

    settings(monkeypatch, TOADS_BOT_SPEC="nope")
    with pytest.raises(SystemExit, match="unknown bot 'nope'"):
        cli.main()


# --------------------------------------------------------------- runner


def test_the_runner_reports_each_actions_result() -> None:
    link = FakeLink([action(action_id=1), action("dance", action_id=2), action(action_id=3)])
    calls: list[int] = []

    async def say(a: SiteAction) -> dict[str, int | str]:
        calls.append(a.id)
        if a.id == 3:
            raise RuntimeError("channel gone")
        return {"message_id": 100 + a.id}

    assert run(ActionRunner("relay", link, {"say": say}).run_once()) == 3
    assert calls == [1, 3]
    assert link.results[1] == ActionResult(refs={"message_id": 101})
    assert link.results[2] == ActionResult(ok=False, error="no handler for dance")
    assert link.results[3] == ActionResult(ok=False, error="RuntimeError: channel gone")


def test_a_hub_outage_skips_the_run() -> None:
    link = MagicMock()
    link.pull = AsyncMock(side_effect=httpx.ConnectError("down"))
    assert run(ActionRunner("relay", link, {}).run_once()) == 0


# ---------------------------------------------------------------- relay


def relay(link: FakeLink, channel: Any = None) -> Relay:
    bot = MagicMock()
    bot.get_channel.return_value = channel
    return Relay(bot, ctx(link))


def test_relay_says_the_sites_text_without_pings() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=SimpleNamespace(id=555))
    link = FakeLink([action(channel_id=CHANNEL, text="@everyone raid at 8")])
    binding = relay(link, channel)
    run(ActionRunner("relay", link, binding.handlers()).run_once())
    channel.send.assert_awaited_once_with("@everyone raid at 8", allowed_mentions=NO_PINGS)
    assert link.results[1] == ActionResult(refs={"channel_id": CHANNEL, "message_id": 555})


def test_relay_refuses_channels_that_are_not_its_own() -> None:
    link = FakeLink([action(channel_id=999, text="hi")])
    run(ActionRunner("relay", link, relay(link, MagicMock(spec=discord.TextChannel)).handlers()).run_once())
    assert link.results[1].ok is False
    assert "not one of this bot's channels" in str(link.results[1].error)


def message(*, channel: int = CHANNEL, guild: int | None = GUILD, bot: bool = False) -> Any:
    return SimpleNamespace(
        id=42,
        content="hello hub",
        author=SimpleNamespace(id=7, bot=bot, display_name="Ribbitz"),
        channel=SimpleNamespace(id=channel),
        guild=SimpleNamespace(id=guild) if guild is not None else None,
    )


def test_relay_passes_member_messages_to_the_site() -> None:
    link = FakeLink()
    run(relay(link).on_message(message()))
    [event] = link.events
    assert (event.event_id, event.kind, event.channel_id, event.user_id, event.guild_id) == (
        "message:42",
        "message",
        CHANNEL,
        7,
        GUILD,
    )
    assert event.payload == {"message_id": 42, "author_name": "Ribbitz", "content": "hello hub"}


@pytest.mark.parametrize("msg", [message(bot=True), message(channel=999), message(guild=None), message(guild=2)])
def test_relay_ignores_bots_other_channels_and_other_servers(msg: Any) -> None:
    link = FakeLink()
    run(relay(link).on_message(msg))
    assert link.events == []


def test_a_binding_cannot_emit_an_event_it_did_not_declare() -> None:
    with pytest.raises(ValueError, match="does not declare"):
        run(relay(FakeLink()).emit("reaction", event_id="r:1"))


# ----------------------------------------------------------------- link


def test_the_http_link_speaks_the_bridge_routes() -> None:
    seen: list[tuple[str, str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, body))
        assert request.headers["Authorization"] == "Bearer svc"
        if request.url.path.endswith("/actions"):
            return httpx.Response(200, json=[action(channel_id=CHANNEL, text="hi").model_dump(mode="json")])
        if request.url.path.endswith("/events"):
            return httpx.Response(202, json={"accepted": True, "duplicate": False, "handled_by": []})
        return httpx.Response(204 if request.method == "POST" else 200, json=body)

    link = HttpHubLink("http://hub/", SecretStr("svc"), transport=httpx.MockTransport(handler))

    async def go() -> None:
        await link.register(RELAY.manifest())
        [pulled] = await link.pull("relay")
        assert pulled.payload == {"channel_id": CHANNEL, "text": "hi"}
        await link.report("relay", pulled.id, ActionResult(refs={"message_id": 5}))
        receipt = await link.send_event(
            "relay", DiscordEvent(event_id="message:1", kind="message", occurred_at=datetime(2026, 9, 28, tzinfo=UTC))
        )
        assert receipt.accepted
        await link.aclose()

    run(go())
    assert [(m, p) for m, p, _ in seen] == [
        ("PUT", "/api/bots/relay"),
        ("GET", "/api/bots/relay/actions"),
        ("POST", "/api/bots/relay/actions/1/result"),
        ("POST", "/api/bots/relay/events"),
    ]
    assert seen[2][2] == {"ok": True, "refs": {"message_id": 5}, "error": None}
