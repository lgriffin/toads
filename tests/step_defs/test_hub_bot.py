"""REQ-HUB-BOT-001..004: a kit bot against the real API, over HTTP, with Discord faked."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import httpx
import pytest
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenarios, then, when
from toads_api.bots.bridge import BridgeError
from toads_api.bots.models import DiscordEvent
from toads_bot.kit import ActionRunner, BotContext, HttpHubLink, OpenGate
from toads_bot.kit.relay import NO_PINGS, Relay
from toads_bot.kit.specs import RELAY

from conftest import HUB, Hub

scenarios(str(Path(__file__).resolve().parents[1] / "features" / "hub_bot.feature"))

BOT = {"Authorization": "Bearer test-service-token"}  # conftest.make_settings


class World:
    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        # The bot reaches the API over HTTP exactly as in production, minus the network.
        hub.app.state.services = hub.services
        self.link = HttpHubLink(HUB, SecretStr("test-service-token"), transport=httpx.ASGITransport(app=hub.app))
        self.channel = MagicMock(spec=discord.TextChannel)
        self.channel.send = AsyncMock(return_value=SimpleNamespace(id=555))
        bot = MagicMock()
        bot.get_channel.side_effect = lambda cid: self.channel if cid == 111 else None
        ctx = BotContext(
            manifest=RELAY.manifest(), guild_id=1, link=self.link, gate=OpenGate(), channel_ids=frozenset({111})
        )
        self.relay = Relay(bot, ctx)
        self.results: list[dict[str, Any]] = []
        self.heard: list[str] = []

    def run(self, coro: Any) -> Any:
        return asyncio.run(coro)


@pytest.fixture
def world(hub: Hub) -> World:
    return World(hub)


@given("the relay bot's spec")
def relay_spec() -> None:
    assert RELAY.bindings == (Relay,)


@when("the bot registers with the hub")
@given("the relay bot is registered and watching channel 111")
def registered(world: World) -> None:
    world.run(world.link.register(RELAY.manifest()))


@then('the hub lists the relay bot with its "say" action and "message" event')
def listed(world: World) -> None:
    [bot] = world.hub.client.get("/api/bots", headers=BOT).json()
    assert (bot["name"], bot["actions"], bot["events"]) == ("relay", ["say"], ["message"])


@when(parsers.parse('the site asks the relay bot to say "{text}" in channel {channel:d}'))
def site_says(world: World, text: str, channel: int) -> None:
    bridge = world.hub.services.bots
    bridge.on_result("relay", "say")(lambda _a, r: world.results.append(dict(r.refs)))
    bridge.send("relay", "say", {"channel_id": channel, "text": text})


@when("the bot runs its pending actions")
def bot_runs(world: World) -> None:
    assert world.run(ActionRunner(RELAY.manifest(), world.link, world.relay.handlers()).run_once()) == 1


@then(parsers.parse('"{text}" is posted in channel {channel:d} without pings'))
def posted(world: World, text: str, channel: int) -> None:
    world.channel.send.assert_awaited_once_with(text, allowed_mentions=NO_PINGS)


@then("the site learns the message id the post became")
def learned(world: World) -> None:
    assert world.results == [{"channel_id": 111, "message_id": 555}]
    assert world.hub.services.bots.pending("relay") == []


@given("a site feature listens for the relay bot's messages")
def listens(world: World) -> None:
    world.hub.services.bots.on_event("relay", "message", name="feature")(
        lambda _bot, e: world.heard.append(str(e.payload["content"]))
    )


@when(parsers.parse('a member writes "{text}" in channel {channel:d} twice over'))
def member_writes(world: World, text: str, channel: int) -> None:
    message = SimpleNamespace(
        id=42,
        content=text,
        author=SimpleNamespace(id=7, bot=False, display_name="Ribbitz"),
        channel=SimpleNamespace(id=channel),
        guild=SimpleNamespace(id=1),
    )
    world.run(world.relay.on_message(message))
    world.run(world.relay.on_message(message))  # a resend after a reconnect carries the same event id


@then(parsers.parse('the site feature hears "{text}" once'))
def hears_once(world: World, text: str) -> None:
    assert world.heard == [text]


@then(parsers.parse('the site cannot ask the relay bot to "{kind}"'))
def refuses_action(world: World, kind: str) -> None:
    with pytest.raises(BridgeError):
        world.hub.services.bots.send("relay", kind)


@then(parsers.parse('the hub refuses a "{kind}" event from the relay bot'))
def refuses_event(world: World, kind: str) -> None:
    event = DiscordEvent(event_id="r:1", kind=kind, occurred_at="2026-09-28T00:00:00Z")
    r = world.hub.client.post("/api/bots/relay/events", headers=BOT, json=event.model_dump(mode="json"))
    assert r.status_code == 422
