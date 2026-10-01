"""An async client for toadsbank-api's v1 HTTP contract (docs/bank.md). It speaks for one member at a time: the hub's
service token proves the call comes from the hub, and the X-Toads-* headers name the member and their hub standing.

No FastAPI or RBAC here: routes turn a Principal into a BankIdentity and BankError into an HTTP answer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import SecretStr

log = logging.getLogger(__name__)

# Statuses whose ToadsBank error the hub passes on as they are (the contract's Errors table). Anything else, a 401
# included (the hub's own token was refused), is the bank being unavailable to the member.
PASSED_ON = frozenset({400, 403, 404, 409, 422, 423})
NAME_LIMIT = 100


@dataclass(frozen=True)
class BankIdentity:
    """Who a call is for: the member's Discord id, display name and contract roles (member, officer, admin)."""

    member: int
    name: str
    roles: tuple[str, ...] = ("member",)

    def headers(self) -> dict[str, str]:
        return {
            "X-Toads-Member": str(self.member),
            # Percent-encoded UTF-8, so any display name fits in a header.
            "X-Toads-Name": quote(self.name[:NAME_LIMIT], safe=""),
            "X-Toads-Roles": ",".join(self.roles),
        }


class BankError(Exception):
    """A ToadsBank answer the member should see, or the bank being unreachable (502) or not set up (503)."""

    def __init__(self, status: int, code: str, message: str, *, details: Any = None, current: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.current = current

    def body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            error["details"] = self.details
        if self.current is not None:
            error["current"] = self.current
        return {"detail": self.message, "error": error}


def not_configured() -> BankError:
    return BankError(503, "bank_not_configured", "The guild bank is not set up on this hub yet")


def _unavailable(why: str) -> BankError:
    return BankError(502, "bank_unavailable", f"The guild bank is not answering ({why}); try again shortly")


def _seg(value: str | int) -> str:
    """One path segment, encoded so an id can never reach another route."""
    return quote(str(value), safe="")


def _error_from(response: httpx.Response) -> BankError:
    status = response.status_code
    if status not in PASSED_ON:
        if status == 401:
            log.error("toadsbank refused the hub's service token")
        return _unavailable(f"HTTP {status}")
    try:
        error = response.json().get("error") or {}
    except ValueError:
        error = {}
    if not isinstance(error, dict):
        error = {}
    code = str(error.get("code") or "bank_error")
    message = str(error.get("message") or "The guild bank refused that")
    return BankError(status, code, message, details=error.get("details"), current=error.get("current"))


class BankClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str, token: SecretStr) -> None:
        self._http = http
        self._base = base_url.rstrip("/")
        self._token = token

    async def call(
        self,
        method: str,
        path: str,
        who: BankIdentity,
        *,
        json: Any = None,
        params: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self._token.get_secret_value()}", **who.headers()}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        try:
            r = await self._http.request(
                method, f"{self._base}/v1{path}", headers=headers, json=json, params=params, timeout=10.0
            )
        except httpx.HTTPError as exc:
            log.warning("toadsbank unreachable: %s", type(exc).__name__)
            raise _unavailable("no connection") from None
        if not r.is_success:
            raise _error_from(r)
        if not r.content:
            return None
        try:
            return r.json()
        except ValueError:
            raise _unavailable("unreadable answer") from None

    # ------------------------------------------------------------------ imports

    async def open_import(self, who: BankIdentity, key: str) -> Any:
        return await self.call("POST", "/imports", who, json={}, idempotency_key=key)

    async def add_parts(self, who: BankIdentity, import_id: str, text: str, key: str) -> Any:
        return await self.call(
            "POST", f"/imports/{_seg(import_id)}/parts", who, json={"text": text}, idempotency_key=key
        )

    async def preview(self, who: BankIdentity, import_id: str) -> Any:
        return await self.call("GET", f"/imports/{_seg(import_id)}/preview", who)

    async def accept(self, who: BankIdentity, import_id: str, key: str) -> Any:
        return await self.call("POST", f"/imports/{_seg(import_id)}/accept", who, json={}, idempotency_key=key)

    # ------------------------------------------------------------------ sources

    async def sources(self, who: BankIdentity) -> Any:
        return await self.call("GET", "/sources", who)

    async def create_source(self, who: BankIdentity, body: dict[str, Any], key: str) -> Any:
        return await self.call("POST", "/sources", who, json=body, idempotency_key=key)

    async def patch_source(self, who: BankIdentity, source_id: str, body: dict[str, Any], key: str) -> Any:
        return await self.call("PATCH", f"/sources/{_seg(source_id)}", who, json=body, idempotency_key=key)

    async def replica(self, who: BankIdentity, source_id: str) -> Any:
        return await self.call("GET", f"/sources/{_seg(source_id)}/replica", who)

    async def inventory(self, who: BankIdentity, q: str | None = None, source_id: str | None = None) -> Any:
        params = {k: v for k, v in {"q": q, "sourceId": source_id}.items() if v}
        return await self.call("GET", "/inventory", who, params=params)

    # ----------------------------------------------------------------- requests

    async def create_request(self, who: BankIdentity, body: dict[str, Any], key: str) -> Any:
        return await self.call("POST", "/requests", who, json=body, idempotency_key=key)

    async def requests(self, who: BankIdentity, scope: str, status: str | None = None) -> Any:
        params = {"scope": scope, **({"status": status} if status else {})}
        return await self.call("GET", "/requests", who, params=params)

    async def act(self, who: BankIdentity, request_id: str, action: str, body: dict[str, Any], key: str) -> Any:
        """cancel, approve, reject or deliveries on one request."""
        return await self.call(
            "POST", f"/requests/{_seg(request_id)}/{_seg(action)}", who, json=body, idempotency_key=key
        )
