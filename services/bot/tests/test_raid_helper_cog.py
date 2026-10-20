"""`/raidhelper import`: the Toad Bot carries a Raid-Helper export to the hub as the member who sent it."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
from pydantic import SecretStr
from toads_bot.cogs.raid_helper import MAX_EXPORT_BYTES, RaidHelper, import_summary, read_export, refusal
from toads_bot.hub import HubClient

NIGHTS = [{"id": "wed", "name": "Wednesday"}, {"id": "sun", "name": "Sunday"}]
EXPORT = {"slots": [{"name": "Tadpole", "userId": "42", "className": "Priest", "specName": "Holy"}]}


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def interaction(user_id: int = 7) -> Any:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def attachment(raw: bytes, size: int | None = None) -> Any:
    return SimpleNamespace(size=len(raw) if size is None else size, read=AsyncMock(return_value=raw))


def hub_answering(status: int, body: object, seen: list[httpx.Request]) -> HubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/public/raid-nights":
            return httpx.Response(200, json=NIGHTS)
        seen.append(request)
        return httpx.Response(status, json=body)

    return HubClient("http://hub", SecretStr("svc"), transport=httpx.MockTransport(handler))


def test_the_export_goes_to_the_hub_as_the_member_who_sent_it() -> None:
    seen: list[httpx.Request] = []
    result = {"added": 1, "updated": 0, "unchanged": 0, "kept": 0, "skipped": 0, "rows": []}
    cog = RaidHelper(hub_answering(200, result, seen))
    i = interaction(user_id=1234)
    run(cog.run_import(i, "sun", attachment(json.dumps(EXPORT).encode("utf-8-sig"))))
    (request,) = seen
    assert request.url.path == "/api/days/sun/comps/raid-helper"
    assert request.headers["x-toads-acting-member"] == "1234"
    assert request.headers["authorization"] == "Bearer svc"
    assert json.loads(request.content) == EXPORT
    assert "1 pre-filled" in i.followup.send.call_args.args[0]


def test_files_that_are_not_exports_never_reach_the_hub() -> None:
    seen: list[httpx.Request] = []
    cog = RaidHelper(hub_answering(200, {}, seen))
    too_big, not_json = interaction(), interaction()
    run(cog.run_import(too_big, "sun", attachment(b"{}", size=MAX_EXPORT_BYTES + 1)))
    run(cog.run_import(not_json, "sun", attachment(b"Tadpole, Priest, Holy")))
    assert seen == []
    assert "too big" in too_big.response.send_message.call_args.args[0]
    assert "not JSON" in not_json.followup.send.call_args.args[0]


def test_a_refusal_is_explained() -> None:
    seen: list[httpx.Request] = []
    i = interaction()
    run(RaidHelper(hub_answering(403, {"detail": "Forbidden"}, seen)).run_import(i, "sun", attachment(b"{}")))
    assert "officers" in i.followup.send.call_args.args[0]
    assert "no sign-ups" in refusal(httpx.Response(422, json={"detail": "That export has no sign-ups in it"}))


def test_read_export_and_summary() -> None:
    assert read_export(b"[1, 2]") is None
    assert read_export(b"\xff") is None
    rows = [{"name": f"Seat{i}", "outcome": "skipped", "reason": "Not confirmed"} for i in range(17)]
    text = import_summary("sun", {"added": 3, "kept": 1, "skipped": 17, "rows": rows})
    assert text.startswith("Raid-Helper import for sun: 3 pre-filled, 1 kept (they set their own on Me), 17 skipped.")
    assert "- Seat0: Not confirmed" in text
    assert "- and 2 more" in text


def test_a_night_typed_by_name_reaches_the_hub_by_id() -> None:
    seen: list[httpx.Request] = []
    result = {"added": 2, "rows": []}
    i = interaction()
    run(RaidHelper(hub_answering(200, result, seen)).run_import(i, " Sunday ", attachment(b"{}")))
    assert [r.url.path for r in seen] == ["/api/days/sun/comps/raid-helper"]
    assert i.followup.send.call_args.args[0].startswith("Raid-Helper import for Sunday: 2 pre-filled")


def test_an_unknown_night_never_reaches_the_hub() -> None:
    seen: list[httpx.Request] = []
    i = interaction()
    run(RaidHelper(hub_answering(200, {}, seen)).run_import(i, "Friday", attachment(b"{}")))
    assert seen == []
    assert "no raid night called Friday" in i.followup.send.call_args.args[0]
