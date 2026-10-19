"""Interview rooms, two-way posts and the hub client, against fake Discord objects and a fake Hub API."""

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
from toads_bot.cogs.community import (
    NO_PINGS,
    Community,
    application_embed,
    find_interviewer,
    interview_channel_name,
    interview_overwrites,
    post_embed,
)
from toads_bot.hub import HubClient

GUILD, MIRRORED, APPLICANT = 1, 111, 10_005


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def cog(hub: Any, *, post: bool = True) -> Community:
    return Community(MagicMock(), hub, guild_id=GUILD, mirror_channel_ids={MIRRORED}, post_to_channels=post)


def message(*, channel: int = MIRRORED, guild: int | None = GUILD, bot: bool = False, content: str = "hi") -> Any:
    return SimpleNamespace(
        id=42,
        content=content,
        created_at=datetime(2026, 9, 26, tzinfo=UTC),
        author=SimpleNamespace(bot=bot, display_name="Ribbitz"),
        channel=SimpleNamespace(id=channel),
        guild=SimpleNamespace(id=guild) if guild is not None else None,
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Mossbeard", "interview-mossbeard"),
        ("Fröggë", "interview-frogge"),
        ("@everyone", "interview-everyone"),
        ("ØØ", "interview-applicant"),
        ("../../x", "interview-x"),
    ],
)
def test_interview_channel_name(name: str, expected: str) -> None:
    assert interview_channel_name(name) == expected


@pytest.mark.security
def test_interview_room_is_private() -> None:
    everyone, applicant, officer, me = (discord.Object(id=i) for i in (1, 2, 3, 4))
    guild = SimpleNamespace(default_role=everyone)
    ow = interview_overwrites(guild, applicant, [officer], me)  # type: ignore[arg-type]
    assert ow[everyone].view_channel is False
    assert ow[applicant].view_channel is True
    assert ow[applicant].mention_everyone is False
    assert ow[officer].send_messages is True
    assert ow[me].manage_channels is True
    assert set(ow) == {everyone, applicant, officer, me}


def test_post_embed_is_capped() -> None:
    e = post_embed({"title": "t" * 300, "body": "b" * 5000, "author_name": "Ribbitz"})
    assert len(e.title or "") == 256
    assert len(e.description or "") == 4096
    assert e.footer.text == "Ribbitz · Toads Hub"


# ------------------------------------------------------------------ inbound


def test_mirrored_message_goes_to_the_hub() -> None:
    hub = AsyncMock()
    run(cog(hub).on_message(message()))
    hub.discord_message.assert_awaited_once()
    assert hub.discord_message.await_args.kwargs["channel_id"] == MIRRORED


@pytest.mark.parametrize(
    "msg",
    [message(bot=True), message(channel=999), message(guild=2), message(guild=None)],
    ids=["own or other bot", "unmirrored channel", "other server", "direct message"],
)
def test_other_messages_stay_in_discord(msg: Any) -> None:
    hub = AsyncMock()
    run(cog(hub).on_message(msg))
    hub.discord_message.assert_not_awaited()


def test_edits_and_deletes_follow() -> None:
    hub = AsyncMock()
    c = cog(hub)
    edit = SimpleNamespace(channel_id=MIRRORED, guild_id=GUILD, message_id=42, message=message(content="edited"))
    run(c.on_raw_message_edit(edit))  # type: ignore[arg-type]
    assert hub.discord_message.await_args.kwargs["content"] == "edited"
    run(c.on_raw_message_delete(SimpleNamespace(channel_id=MIRRORED, guild_id=GUILD, message_id=42)))  # type: ignore[arg-type]
    hub.discord_message_deleted.assert_awaited_once_with(42)
    run(c.on_raw_message_delete(SimpleNamespace(channel_id=999, guild_id=GUILD, message_id=43)))  # type: ignore[arg-type]
    assert hub.discord_message_deleted.await_count == 1


# ----------------------------------------------------------------- outbound


def fake_guild(channel: Any = None) -> Any:
    applicant = MagicMock(mention=f"<@{APPLICANT}>", id=APPLICANT)
    created = MagicMock(id=6001)
    created.send = AsyncMock()
    officer_role = discord.Object(id=12)
    guild = MagicMock()
    guild.default_role = discord.Object(id=GUILD)
    guild.me = discord.Object(id=99)
    guild.get_member.return_value = applicant
    guild.get_role.side_effect = lambda rid: officer_role if rid == 12 else None
    guild.get_channel.return_value = channel
    guild.create_text_channel = AsyncMock(return_value=created)
    guild.created = created
    return guild


def job(kind: str, payload: dict[str, Any], post: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"job": {"id": 7, "kind": kind, "payload": payload}, "post": post}


def test_opens_an_interview_room_and_acks_it() -> None:
    hub = AsyncMock()
    hub.outbox.return_value = [
        job(
            "create_interview_room",
            {
                "application_id": 3,
                "discord_user_id": APPLICANT,
                "character_name": "Mossbeard",
                "category_id": None,
                "officer_role_ids": [12, 404],
            },
        )
    ]
    guild = fake_guild()
    run(cog(hub).run_outbox(guild))
    name = guild.create_text_channel.await_args.args[0]
    overwrites = guild.create_text_channel.await_args.kwargs["overwrites"]
    assert name == "interview-mossbeard"
    assert {getattr(k, "id", None) for k in overwrites} == {GUILD, APPLICANT, 12, 99}  # unknown role 404 skipped
    hub.ack.assert_awaited_once_with(7, channel_id=6001)
    # The welcome pings only the applicant.
    mentions = guild.created.send.await_args.kwargs["allowed_mentions"]
    assert (mentions.everyone, mentions.roles) == (False, False)


def test_named_interviewers_join_the_room_with_the_answers() -> None:
    gallagher = MagicMock(mention="<@501>", id=501)
    gallagher.name = "_gallagher"
    hadur = MagicMock(mention="<@502>", id=502)
    hadur.name = "hadur117"
    lookalike = MagicMock(mention="<@503>", id=503, nick="hadur117")  # a nickname is not a username
    lookalike.name = "someone"
    hub = AsyncMock()
    hub.outbox.return_value = [
        job(
            "create_interview_room",
            {
                "application_id": 3,
                "discord_user_id": APPLICANT,
                "character_name": "Mossbeard",
                "category_id": None,
                "officer_role_ids": [],
                "interviewers": ["_gallagher", "hadur117", "ghost"],
                "class_name": "Shaman",
                "role": "Healer",
                "secondary_role": "Ranged",
                "why_toads": "Friends raid here.",
            },
        )
    ]
    guild = fake_guild()
    guild.members = [lookalike, gallagher, hadur]
    guild.query_members = AsyncMock(return_value=[])  # "ghost" is not in the server at all
    run(cog(hub).run_outbox(guild))
    overwrites = guild.create_text_channel.await_args.kwargs["overwrites"]
    assert {getattr(k, "id", None) for k in overwrites} == {GUILD, APPLICANT, 501, 502, 99}
    assert overwrites[gallagher].send_messages is True
    sent = guild.created.send.await_args
    assert sent.args[0].startswith(f"<@{APPLICANT}> <@501> <@502> Welcome")
    assert "Could not find ghost" in sent.args[0]
    mentions = sent.kwargs["allowed_mentions"]
    assert (mentions.everyone, mentions.roles, mentions.users) == (
        False,
        False,
        [guild.get_member.return_value, gallagher, hadur],
    )
    fields = {f.name: f.value for f in sent.kwargs["embed"].fields}
    assert fields == {"Class": "Shaman", "Roles": "Healer, then Ranged", "Why Toads?": "Friends raid here."}
    hub.ack.assert_awaited_once_with(7, channel_id=6001)


def test_interviewers_can_be_named_by_user_id() -> None:
    guild = MagicMock()
    run(find_interviewer(guild, "123456789012345678"))
    guild.get_member.assert_called_once_with(123456789012345678)


def test_interviewers_missing_from_the_cache_are_asked_of_discord() -> None:
    fetched = MagicMock(id=501)
    guild = MagicMock(members=[])
    guild.get_member.return_value = None
    guild.fetch_member = AsyncMock(return_value=fetched)
    assert run(find_interviewer(guild, "501")) is fetched
    guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(status=404), "Unknown Member"))
    assert run(find_interviewer(guild, "502")) is None

    hadur, lookalike = MagicMock(), MagicMock()
    hadur.name, lookalike.name = "hadur117", "hadur1170"
    guild.query_members = AsyncMock(return_value=[lookalike, hadur])
    assert run(find_interviewer(guild, "hadur117")) is hadur
    guild.query_members.assert_awaited_once_with(query="hadur117", limit=10)


def test_application_embed_copes_with_an_older_job_and_long_answers() -> None:
    old = application_embed({"application_id": 1, "character_name": "Mossbeard"})
    assert [f.value for f in old.fields] == ["?", "?", "Not answered"]
    long = application_embed({"application_id": 1, "character_name": "M", "why_toads": "x" * 2000})
    assert len(long.fields[2].value) == 1024


def test_locks_a_closed_interview_room() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    applicant, officers = discord.Object(id=APPLICANT), discord.Object(id=12)
    channel.overwrites = {applicant: discord.PermissionOverwrite(send_messages=True), officers: MagicMock()}
    channel.edit = AsyncMock()
    hub = AsyncMock()
    hub.outbox.return_value = [job("lock_interview_room", {"channel_id": 6001, "discord_user_id": APPLICANT})]
    run(cog(hub).run_outbox(fake_guild(channel)))
    new = channel.edit.await_args.kwargs["overwrites"]
    assert new[applicant].send_messages is False
    assert new[applicant].view_channel is True
    assert new[officers] is channel.overwrites[officers]
    hub.ack.assert_awaited_once_with(7)


POST = {"title": "Patch day", "body": "No raid @everyone", "author_name": "Ribbitz"}


@pytest.mark.security
def test_posts_never_ping() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=MagicMock(id=8001))
    hub = AsyncMock()
    hub.outbox.return_value = [job("post_message", {"post_id": 1, "channel_id": 333}, POST)]
    run(cog(hub).run_outbox(fake_guild(channel)))
    assert channel.send.await_args.kwargs["allowed_mentions"] is NO_PINGS
    assert NO_PINGS.everyone is False and NO_PINGS.roles is False and NO_PINGS.users is False
    hub.ack.assert_awaited_once_with(7, message_id=8001)


def test_edits_follow_hub_edits() -> None:
    sent = MagicMock()
    sent.edit = AsyncMock()
    channel = MagicMock(spec=discord.TextChannel)
    channel.fetch_message = AsyncMock(return_value=sent)
    hub = AsyncMock()
    hub.outbox.return_value = [job("edit_message", {"post_id": 1, "channel_id": 333, "message_id": 8001}, POST)]
    run(cog(hub).run_outbox(fake_guild(channel)))
    channel.fetch_message.assert_awaited_once_with(8001)
    assert sent.edit.await_args.kwargs["allowed_mentions"] is NO_PINGS
    hub.ack.assert_awaited_once_with(7)


def test_posting_waits_for_the_feature_flag() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    hub = AsyncMock()
    hub.outbox.return_value = [job("post_message", {"post_id": 1, "channel_id": 333}, POST)]
    run(cog(hub, post=False).run_outbox(fake_guild(channel)))
    channel.send.assert_not_awaited()
    hub.ack.assert_not_awaited()


def test_failed_job_is_retried_not_acked() -> None:
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=500, reason="x"), "boom"))
    hub = AsyncMock()
    hub.outbox.return_value = [job("post_message", {"post_id": 1, "channel_id": 333}, POST)]
    run(cog(hub).run_outbox(fake_guild(channel)))
    hub.ack.assert_not_awaited()


# --------------------------------------------------------------- hub client


def test_hub_client_sends_the_service_token_and_caps_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[] if request.method == "GET" else {})

    async def go() -> None:
        hub = HubClient("http://api:8000/", SecretStr("svc"), transport=httpx.MockTransport(handler))
        await hub.outbox()
        await hub.ack(7, channel_id=6001)
        await hub.discord_message(
            channel_id=1, message_id=2, author_name="a" * 200, content="c" * 5000, created_at=datetime.now(UTC)
        )
        await hub.discord_message_deleted(2)
        await hub.aclose()

    run(go())
    assert [r.url.path for r in seen] == [
        "/api/bot/outbox",
        "/api/bot/outbox/7/ack",
        "/api/bot/discord-messages",
        "/api/bot/discord-messages/2/deleted",
    ]
    assert all(r.headers["authorization"] == "Bearer svc" for r in seen)
    assert json.loads(seen[1].content) == {"channel_id": 6001}
    body = json.loads(seen[2].content)
    assert (len(body["author_name"]), len(body["content"])) == (100, 4000)
