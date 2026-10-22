"""`/highlight`, `/stream` and `/clip`: the Toad Bot carries a member's photo, stream link or clip to the hub's
Highlights page, as that member."""

from __future__ import annotations

import asyncio
import base64
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import discord
import httpx
from pydantic import SecretStr
from toads_bot.cogs.highlights import Highlights, refusal
from toads_bot.hub import HubClient

STREAM = {"id": 3, "streamer_name": "Hopscotch", "channel": "hopscotch", "title": "Sunday Gruul"}


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def interaction(user_id: int = 7) -> Any:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        channel=SimpleNamespace(send=AsyncMock()),
        channel_id=99,
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def attachment(content_type: str | None = "image/png", size: int = 100, data: bytes = b"photo") -> Any:
    return SimpleNamespace(content_type=content_type, size=size, read=AsyncMock(return_value=data))


def hub_answering(status: int, body: object, seen: list[httpx.Request]) -> HubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body)

    return HubClient("http://hub", SecretStr("svc"), transport=httpx.MockTransport(handler))


def test_a_photo_goes_to_the_hub_as_the_member_who_posted_it() -> None:
    seen: list[httpx.Request] = []
    i = interaction(user_id=1234)
    cog = Highlights(hub_answering(201, {"id": 1}, seen), "https://toads.gg/")
    run(cog.post_photo(i, attachment(data=b"\x89PNG..."), "Gruul down!"))
    (request,) = seen
    assert (request.method, request.url.path) == ("POST", "/api/gallery/photos")
    assert request.headers["x-toads-acting-member"] == "1234"
    assert request.headers["authorization"] == "Bearer svc"
    body = json.loads(request.content)
    assert (body["caption"], base64.b64decode(body["image_base64"])) == ("Gruul down!", b"\x89PNG...")
    answer = i.followup.send.call_args
    assert "https://toads.gg/highlights" in answer.args[0] and "48 hours" in answer.args[0]
    assert answer.kwargs["ephemeral"] is True


def test_a_photo_waiting_for_an_officer_says_so() -> None:
    i = interaction()
    run(Highlights(hub_answering(201, {"id": 1, "waiting": True}, [])).post_photo(i, attachment(), ""))
    assert "once they approve it" in i.followup.send.call_args.args[0]


def test_what_is_not_a_photo_never_reaches_the_hub() -> None:
    seen: list[httpx.Request] = []
    cog = Highlights(hub_answering(201, {}, seen))
    for bad in (attachment("application/pdf"), attachment(None), attachment(size=11 * 1024 * 1024)):
        i = interaction()
        run(cog.post_photo(i, bad, ""))
        assert i.response.send_message.call_args.kwargs["ephemeral"] is True
    assert seen == []


def test_a_refusal_is_explained() -> None:
    i = interaction()
    run(Highlights(hub_answering(403, {"detail": "Not a member"}, [])).post_photo(i, attachment(), ""))
    assert "raiders" in i.followup.send.call_args.args[0]
    assert "not a photo" in refusal(httpx.Response(422, json={"detail": "That file is not a photo the hub can read"}))
    assert "(500)" in refusal(httpx.Response(500, text="boom"))


def test_a_stream_is_announced_in_the_channel_without_pings() -> None:
    seen: list[httpx.Request] = []
    i = interaction(user_id=55)
    run(Highlights(hub_answering(201, STREAM, seen)).start_stream(i, "twitch.tv/hopscotch", "Sunday Gruul"))
    (request,) = seen
    assert request.url.path == "/api/gallery/streams"
    assert request.headers["x-toads-acting-member"] == "55"
    assert json.loads(request.content) == {"link": "twitch.tv/hopscotch", "title": "Sunday Gruul"}
    assert i.response.defer.await_args.kwargs["ephemeral"] is True
    announced = i.channel.send.call_args
    assert "Hopscotch is live on Twitch: Sunday Gruul" in announced.args[0]
    assert "https://www.twitch.tv/hopscotch" in announced.args[0]
    assert announced.kwargs["allowed_mentions"].everyone is False
    assert i.followup.send.call_args.kwargs["ephemeral"] is True


def test_a_stream_the_bot_cannot_announce_is_still_on_the_page() -> None:
    i = interaction()
    response = SimpleNamespace(status=403, reason="Forbidden")
    i.channel.send.side_effect = discord.Forbidden(response, "Missing Permissions")  # type: ignore[arg-type]
    run(Highlights(hub_answering(201, STREAM, [])).start_stream(i, "twitch.tv/hopscotch", ""))
    assert "could not announce" in i.followup.send.call_args.args[0]
    assert i.followup.send.call_args.kwargs["ephemeral"] is True


def test_a_stream_waiting_for_an_officer_is_not_announced() -> None:
    i = interaction()
    run(Highlights(hub_answering(201, {**STREAM, "waiting": True}, [])).start_stream(i, "twitch.tv/hopscotch", ""))
    i.channel.send.assert_not_called()
    answer = i.followup.send.call_args
    assert "approve twitch.tv/hopscotch" in answer.args[0] and answer.kwargs["ephemeral"] is True


def test_a_bad_stream_link_is_answered_privately() -> None:
    i = interaction()
    detail = {"detail": "Give your Twitch channel's link, like https://twitch.tv/yourname"}
    run(Highlights(hub_answering(422, detail, [])).start_stream(i, "https://evil.example", ""))
    assert "Twitch channel's link" in i.followup.send.call_args.args[0]
    assert i.followup.send.call_args.kwargs["ephemeral"] is True


def test_ending_a_stream_says_whether_there_was_one() -> None:
    seen: list[httpx.Request] = []
    i = interaction()
    run(Highlights(hub_answering(200, {"ended": 1}, seen)).end_stream(i))
    assert seen[0].url.path == "/api/gallery/streams/end"
    assert "off the Highlights page" in i.followup.send.call_args.args[0]
    i = interaction()
    run(Highlights(hub_answering(200, {"ended": 0}, [])).end_stream(i))
    assert "no stream" in i.followup.send.call_args.args[0]


def test_a_clip_goes_to_review() -> None:
    seen: list[httpx.Request] = []
    i = interaction(user_id=9)
    run(Highlights(hub_answering(201, {"id": 4}, seen)).share_clip(i, "https://youtu.be/dQw4w9WgXcQ", "Prince"))
    (request,) = seen
    assert (request.url.path, request.headers["x-toads-acting-member"]) == ("/api/highlights", "9")
    assert json.loads(request.content) == {"url": "https://youtu.be/dQw4w9WgXcQ", "title": "Prince"}
    assert "with the officers" in i.followup.send.call_args.args[0]


def test_an_unreachable_hub_is_said_plainly() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    cog = Highlights(HubClient("http://hub", SecretStr("svc"), transport=httpx.MockTransport(down)))
    for call in (
        lambda i: cog.post_photo(i, attachment(), ""),
        lambda i: cog.start_stream(i, "twitch.tv/hop", ""),
        lambda i: cog.end_stream(i),
        lambda i: cog.share_clip(i, "https://youtu.be/dQw4w9WgXcQ", "x"),
    ):
        i = interaction()
        run(call(i))
        assert "not answering" in i.followup.send.call_args.args[0]
