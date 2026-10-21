"""`/bankrequest`: the Toad Bot carries a member's ask for an item to the hub's bank desk, as that member."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
from pydantic import SecretStr
from toads_bot.cogs.bank_desk import BankDesk, receipt, refusal
from toads_bot.hub import HubClient

ASKED = {"id": 12, "item": "Flask of Relentless Assault", "quantity": 4, "status": "pending"}


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def interaction(user_id: int = 7) -> Any:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def hub_answering(status: int, body: object, seen: list[httpx.Request]) -> HubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body)

    return HubClient("http://hub", SecretStr("svc"), transport=httpx.MockTransport(handler))


def test_the_request_goes_to_the_hub_as_the_member_who_asked() -> None:
    seen: list[httpx.Request] = []
    i = interaction(user_id=1234)
    run(BankDesk(hub_answering(201, ASKED, seen)).ask(i, "Flask of Relentless Assault", 4))
    (request,) = seen
    assert (request.method, request.url.path) == ("POST", "/api/bank-desk/requests")
    assert request.headers["x-toads-acting-member"] == "1234"
    assert request.headers["authorization"] == "Bearer svc"
    assert json.loads(request.content) == {"item": "Flask of Relentless Assault", "quantity": 4}
    assert i.response.defer.await_args.kwargs["ephemeral"] is True
    answer = i.followup.send.call_args
    assert answer.args[0] == receipt(ASKED)
    assert "#12" in answer.args[0] and "x4" in answer.args[0]
    assert answer.kwargs["ephemeral"] is True


def test_a_refusal_is_explained() -> None:
    i = interaction()
    run(BankDesk(hub_answering(403, {"detail": "Not a member of the guild"}, [])).ask(i, "Drums", 1))
    assert "members of the Toads Discord" in i.followup.send.call_args.args[0]
    assert "at most 100" in refusal(httpx.Response(422, json={"detail": "An item name is at most 100 characters"}))
    assert "(500)" in refusal(httpx.Response(500, text="boom"))


def test_an_unreachable_hub_is_said_plainly() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    i = interaction()
    run(BankDesk(HubClient("http://hub", SecretStr("svc"), transport=httpx.MockTransport(down))).ask(i, "Drums", 1))
    assert "not answering" in i.followup.send.call_args.args[0]
