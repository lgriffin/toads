"""The bank bot's door into the hub's /api/bank routes. It calls with the service token and names the Discord member
who used the command or button in `X-Toads-Acting-Member`; the hub reads that member's roles from Discord itself, so
the bot can do nothing the member could not do on the site (docs/bank.md)."""

from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import quote

import httpx
from pydantic import SecretStr

ACTING_MEMBER = "X-Toads-Acting-Member"


class BankApiError(Exception):
    """The hub (or ToadsBank behind it) refused: `code` is ToadsBank's error code, or the hub's when it answered."""

    def __init__(self, status: int, code: str, message: str, details: Any = None, current: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.current = current


class BankApi(Protocol):
    async def me(self, member: int) -> dict[str, Any]: ...
    async def open_import(self, member: int, day: str, key: str) -> dict[str, Any]: ...
    async def add_parts(self, member: int, day: str, import_id: str, text: str, key: str) -> dict[str, Any]: ...
    async def preview(self, member: int, day: str, import_id: str) -> dict[str, Any]: ...
    async def accept(self, member: int, day: str, import_id: str, key: str) -> dict[str, Any]: ...
    async def inventory(self, member: int, q: str) -> dict[str, Any]: ...
    async def create_request(self, member: int, body: dict[str, Any], key: str) -> dict[str, Any]: ...
    async def manage(
        self, member: int, day: str, request_id: str, action: str, body: dict[str, Any], key: str
    ) -> dict[str, Any]: ...
    async def redeem(self, member: int, token: str) -> dict[str, Any]: ...


def _seg(value: str) -> str:
    return quote(value, safe="")


def _error(response: httpx.Response) -> BankApiError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return BankApiError(
            response.status_code,
            str(error.get("code") or "error"),
            str(error.get("message") or "The bank refused that"),
            error.get("details"),
            error.get("current"),
        )
    detail = body.get("detail") if isinstance(body, dict) else None
    message = detail if isinstance(detail, str) else f"The hub answered HTTP {response.status_code}"
    return BankApiError(response.status_code, f"http_{response.status_code}", message)


class HttpBankApi:
    def __init__(self, base_url: str, token: SecretStr, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            timeout=15.0,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _call(
        self,
        method: str,
        path: str,
        member: int,
        *,
        json: Any = None,
        params: dict[str, str] | None = None,
        key: str | None = None,
    ) -> dict[str, Any]:
        headers = {ACTING_MEMBER: str(int(member))}
        if key is not None:
            headers["Idempotency-Key"] = key[:128]
        try:
            r = await self._http.request(method, path, headers=headers, json=json, params=params)
        except httpx.HTTPError:
            raise BankApiError(0, "hub_unreachable", "The hub is not answering; try again shortly") from None
        if not r.is_success:
            raise _error(r)
        data: dict[str, Any] = r.json()
        return data

    async def me(self, member: int) -> dict[str, Any]:
        return await self._call("GET", "/api/bank/me", member)

    async def open_import(self, member: int, day: str, key: str) -> dict[str, Any]:
        return await self._call("POST", f"/api/days/{_seg(day)}/bank/imports", member, key=key)

    async def add_parts(self, member: int, day: str, import_id: str, text: str, key: str) -> dict[str, Any]:
        path = f"/api/days/{_seg(day)}/bank/imports/{_seg(import_id)}/parts"
        return await self._call("POST", path, member, json={"text": text}, key=key)

    async def preview(self, member: int, day: str, import_id: str) -> dict[str, Any]:
        return await self._call("GET", f"/api/days/{_seg(day)}/bank/imports/{_seg(import_id)}/preview", member)

    async def accept(self, member: int, day: str, import_id: str, key: str) -> dict[str, Any]:
        return await self._call("POST", f"/api/days/{_seg(day)}/bank/imports/{_seg(import_id)}/accept", member, key=key)

    async def inventory(self, member: int, q: str) -> dict[str, Any]:
        return await self._call("GET", "/api/bank/inventory", member, params={"q": q})

    async def create_request(self, member: int, body: dict[str, Any], key: str) -> dict[str, Any]:
        return await self._call("POST", "/api/bank/requests", member, json=body, key=key)

    async def manage(
        self, member: int, day: str, request_id: str, action: str, body: dict[str, Any], key: str
    ) -> dict[str, Any]:
        path = f"/api/days/{_seg(day)}/bank/requests/{_seg(request_id)}/{_seg(action)}"
        return await self._call("POST", path, member, json=body, key=key)

    async def redeem(self, member: int, token: str) -> dict[str, Any]:
        """An officer token for the grants it names (docs/admin.md); the hub answers every bad token the same way."""
        return await self._call("POST", "/api/bank/redeem", member, json={"token": token})
