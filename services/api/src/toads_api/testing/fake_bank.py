"""An in-memory toadsbank-api for the dev stack and tests: the v1 HTTP contract (docs/bank.md), small enough to read.

It implements imports (the TOADSBANK/1 paste transport, reassembly and CRC check, preview, accept), sources, the
replica, inventory and requests (reserve, waitlist, cancel, approve, reject, deliveries) with idempotency keys and
revisions. Accepted snapshots and request changes become outbox events: kept in `FakeBankState.events` and, when
`events_url` is set, POSTed to the hub's /api/bank/events the way ToadsBank's worker does.

It is not ToadsBank. Rules the real service owns (raid allocations, expiry, baseline history, stock movement
matching) are left out or simplified, and nothing persists. The dev stack runs
`uvicorn --factory toads_api.testing.fake_bank:app_from_env`, which refuses to start without FAKE_BANK_I_AM_DEV=1.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import itertools
import json
import logging
import os
import re
import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

CHUNK = 1269
MAX_PARTS = 800
MAX_BYTES = 1 << 20
SESSION_SECONDS = 30 * 60
WARN_SECONDS = 24 * 3600
STALE_SECONDS = 72 * 3600
OPEN = ("reserved", "approved", "waitlisted")
HEADER = re.compile(r"^TOADSBANK/(\d+) export=(\S+) part=(\d+)/(\d+) crc32=([0-9a-f]{8})$")
EXPORT_ID = re.compile(r"^[A-Za-z0-9-]{8,48}$")
LINK_NAME = re.compile(r"\|h\[(.+?)\]\|h")
log = logging.getLogger(__name__)


class BankFault(Exception):
    def __init__(self, status: int, code: str, message: str, *, details: Any = None, current: Any = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.details, self.current = status, code, message, details, current


# ------------------------------------------------------------------ transport


def encode_parts(snapshot: dict[str, Any]) -> list[str]:
    """A snapshot as the addon exports it: TOADSBANK/1 parts, each a header line and a base64 line."""
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    crc = f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}"
    chunks = [payload[i : i + CHUNK] for i in range(0, len(payload), CHUNK)] or [b""]
    total = len(chunks)
    return [
        f"TOADSBANK/1 export={snapshot['snapshotId']} part={n}/{total} crc32={crc}\n{base64.b64encode(chunk).decode()}"
        for n, chunk in enumerate(chunks, 1)
    ]


@dataclass
class _Part:
    export: str
    n: int
    total: int
    crc: str
    data: str


def _transport_error(code: str) -> BankFault:
    return BankFault(
        422, "transport_error", f"The pasted text is not a readable export ({code})", details={"code": code}
    )


def read_parts(text: str) -> list[_Part]:
    """Every part in a paste: text before the first header, blank lines, code fences and quote markers are ignored."""
    parts: list[_Part] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip(">").strip().strip("`").strip()
        if not line:
            continue
        if line.startswith("TOADSBANK/"):
            m = HEADER.match(line)
            if m is None or not EXPORT_ID.match(m.group(2)):
                raise _transport_error("bad_header")
            if m.group(1) != "1":
                raise _transport_error("unsupported_version")
            n, total = int(m.group(3)), int(m.group(4))
            if total > MAX_PARTS:
                raise _transport_error("too_many_parts")
            if not 1 <= n <= total:
                raise _transport_error("bad_part_number")
            parts.append(_Part(m.group(2), n, total, m.group(5), ""))
        elif parts:
            parts[-1].data += line
    return parts


# ---------------------------------------------------------------------- state


@dataclass
class _Import:
    id: str
    member: str
    opened_at: int
    export: str | None = None
    total: int = 0
    crc: str = ""
    parts: dict[int, str] = field(default_factory=dict)
    snapshot: dict[str, Any] | None = None


@dataclass
class FakeBankState:
    token: str = "replace-me"  # noqa: S105 - the fake's own placeholder, not a credential
    clock: Callable[[], float] = time.time
    events_url: str = ""
    # Tests deliver events in-process; None uses the network.
    events_transport: httpx.AsyncBaseTransport | None = None
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    # source id -> the accepted snapshot whose tabs the replica shows
    snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)
    imports: dict[str, _Import] = field(default_factory=dict)
    requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    # source id -> item id -> quantity delivered since the source's last accepted snapshot
    outgoing: dict[str, dict[int, int]] = field(default_factory=dict)
    idempotency: dict[str, tuple[str, int, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))

    def now(self) -> int:
        return int(self.clock())

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{next(self._ids)}"

    def add_source(self, **fields: Any) -> dict[str, Any]:
        source = {
            "id": self.next_id("src"),
            "revision": 1,
            "name": fields.get("name", "Guild bank"),
            "kind": "guildBank",
            "guild": fields["guild"],
            "realm": fields["realm"],
            "region": fields["region"],
            "audience": fields.get("audience", "members"),
            "raidDay": fields.get("raidDay"),
            "managers": [str(m) for m in fields.get("managers", [])],
        }
        self.sources[source["id"]] = source
        return source

    def store_snapshot(self, source_id: str, snapshot: dict[str, Any]) -> None:
        self.snapshots[source_id] = snapshot
        self.outgoing[source_id] = {}

    def emit(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {"id": self.next_id("evt"), "type": kind, "occurredAt": self.now(), "payload": payload}
        self.events.append(event)
        return event


# --------------------------------------------------------------------- views


def _observed_at(snapshot: dict[str, Any]) -> int:
    return int(max((t.get("observedAt") or 0 for t in snapshot.get("tabs", [])), default=snapshot["completedAt"]))


def _freshness(state: FakeBankState, observed: int | None) -> str:
    if observed is None:
        return "stale"
    age = state.now() - observed
    return "stale" if age > STALE_SECONDS else "warn" if age > WARN_SECONDS else "fresh"


def _source_view(state: FakeBankState, source: dict[str, Any]) -> dict[str, Any]:
    snapshot = state.snapshots.get(source["id"])
    observed = _observed_at(snapshot) if snapshot else None
    tabs = [
        {k: t.get(k) for k in ("index", "name", "status", "observedAt", "capacity")}
        for t in (snapshot or {}).get("tabs", [])
    ]
    return {**source, "lastObservedAt": observed, "freshness": _freshness(state, observed), "tabs": tabs}


def _item_name(slot: dict[str, Any]) -> str:
    m = LINK_NAME.search(str(slot.get("link") or ""))
    return m.group(1) if m else f"Item {slot['itemId']}"


@dataclass(frozen=True)
class Who:
    member: str
    name: str
    roles: frozenset[str]

    @property
    def admin(self) -> bool:
        return "admin" in self.roles

    def manages(self, source: dict[str, Any]) -> bool:
        return self.admin or self.member in source["managers"]

    def sees(self, source: dict[str, Any]) -> bool:
        return source["audience"] == "members" or "officer" in self.roles or self.manages(source)


def _visible(state: FakeBankState, who: Who) -> list[dict[str, Any]]:
    return [s for s in state.sources.values() if who.sees(s)]


def _held(state: FakeBankState, source_id: str, item_id: int) -> int:
    return sum(
        r["outstanding"]
        for r in state.requests.values()
        if r["sourceId"] == source_id and r["itemId"] == item_id and r["status"] in ("reserved", "approved")
    )


def _stock(state: FakeBankState, source_id: str) -> dict[int, dict[str, Any]]:
    """Per item in one source: name, observed count, pending outgoing, reserved and available."""
    snapshot = state.snapshots.get(source_id)
    items: dict[int, dict[str, Any]] = {}
    for tab in (snapshot or {}).get("tabs", []):
        for slot in tab.get("slots", []):
            entry = items.setdefault(
                int(slot["itemId"]), {"name": _item_name(slot), "observed": 0, "observedAt": tab.get("observedAt")}
            )
            entry["observed"] += int(slot["count"])
    for item_id, entry in items.items():
        entry["pendingOutgoing"] = state.outgoing.get(source_id, {}).get(item_id, 0)
        entry["raidHeld"] = 0
        entry["directReserved"] = _held(state, source_id, item_id)
        entry["available"] = max(0, entry["observed"] - entry["pendingOutgoing"] - entry["directReserved"])
    return items


def inventory(state: FakeBankState, who: Who, q: str = "", source_id: str = "") -> dict[str, Any]:
    merged: dict[int, dict[str, Any]] = {}
    times: list[int] = []
    for source in _visible(state, who):
        if (source_id and source["id"] != source_id) or source["id"] not in state.snapshots:
            continue
        times.append(_observed_at(state.snapshots[source["id"]]))
        for item_id, s in _stock(state, source["id"]).items():
            if q and q.lower() not in s["name"].lower():
                continue
            row = merged.setdefault(
                item_id,
                {
                    "itemId": item_id,
                    "name": s["name"],
                    "observed": 0,
                    "pendingOutgoing": 0,
                    "raidHeld": 0,
                    "directReserved": 0,
                    "available": 0,
                    "sources": [],
                },
            )
            for k in ("observed", "pendingOutgoing", "raidHeld", "directReserved", "available"):
                row[k] += s[k]
            row["sources"].append({"sourceId": source["id"], **{k: v for k, v in s.items() if k != "name"}})
    return {
        "range": {"oldest": min(times), "newest": max(times)} if times else None,
        "items": sorted(merged.values(), key=lambda r: r["name"]),
    }


# ------------------------------------------------------------------ requests


def _bump(state: FakeBankState, req: dict[str, Any], **changes: Any) -> dict[str, Any]:
    req.update(changes, revision=req["revision"] + 1, updatedAt=state.now())
    return req


def _changed(state: FakeBankState, req: dict[str, Any], change: str) -> None:
    state.emit("request.updated", {"request": dict(req), "change": change})


def _expect(req: dict[str, Any], body: dict[str, Any]) -> None:
    if body.get("expectedRevision") != req["revision"]:
        raise BankFault(409, "stale_revision", "This request changed since you loaded it", current=dict(req))


def create_request(state: FakeBankState, who: Who, body: dict[str, Any]) -> dict[str, Any]:
    source = state.sources.get(str(body.get("sourceId")))
    if source is None or not who.sees(source):
        raise BankFault(404, "not_found", "No such source")
    qty = int(body.get("quantity") or 0)
    if qty < 1 or not str(body.get("character") or "").strip():
        raise BankFault(400, "validation_failed", "A request needs a quantity and a character")
    snapshot = state.snapshots.get(source["id"])
    if snapshot is None or _freshness(state, _observed_at(snapshot)) == "stale":
        raise BankFault(423, "source_stale", "This bank has not been captured recently enough to reserve from")
    stock = _stock(state, source["id"]).get(int(body["itemId"]))
    if stock is None:
        raise BankFault(404, "not_found", "That item is not in this bank")
    waitlist = bool(body.get("waitlist"))
    if qty > stock["available"] and not waitlist:
        raise BankFault(
            409,
            "insufficient_stock",
            "Not enough in stock",
            details={"available": stock["available"], "canWaitlist": True},
        )
    now = state.now()
    req = {
        "id": state.next_id("req"),
        "revision": 1,
        "status": "waitlisted" if waitlist else "reserved",
        "memberId": who.member,
        "memberName": who.name,
        "character": str(body["character"]).strip(),
        "sourceId": source["id"],
        "itemId": int(body["itemId"]),
        "itemName": stock["name"],
        "quantity": qty,
        "delivered": 0,
        "outstanding": qty,
        "occurrenceId": body.get("occurrenceId"),
        "note": body.get("note") or "",
        "managerNote": None,
        "managers": list(source["managers"]),
        "createdAt": now,
        "updatedAt": now,
    }
    state.requests[req["id"]] = req
    state.emit("request.created", {"request": dict(req)})
    if req["managers"]:
        state.emit("request.assigned", {"request": dict(req), "managers": list(req["managers"])})
    return req


def act(state: FakeBankState, who: Who, request_id: str, action: str, body: dict[str, Any]) -> dict[str, Any]:
    req = state.requests.get(request_id)
    if req is None:
        raise BankFault(404, "not_found", "No such request")
    source = state.sources[req["sourceId"]]
    manager = who.manages(source)
    if not manager and not (action == "cancel" and req["memberId"] == who.member):
        raise BankFault(403, "forbidden", "Only this bank's managers can do that")
    _expect(req, body)
    if req["status"] not in OPEN or (action in ("approve", "deliveries") and req["status"] == "waitlisted"):
        raise BankFault(409, "invalid_transition", f"A {req['status']} request cannot be changed that way")
    if action == "cancel":
        _bump(state, req, status="cancelled", outstanding=0)
        _changed(state, req, "cancelled")
    elif action in ("approve", "reject"):
        status = "approved" if action == "approve" else "rejected"
        extra = {"outstanding": 0} if action == "reject" else {}
        _bump(state, req, status=status, managerNote=body.get("note"), **extra)
        _changed(state, req, status)
    elif action == "deliveries":
        qty = int(body.get("quantity") or 0)
        if not 1 <= qty <= req["outstanding"]:
            raise BankFault(409, "over_allocated", "That is more than the request has outstanding")
        out = state.outgoing.setdefault(req["sourceId"], {})
        out[req["itemId"]] = out.get(req["itemId"], 0) + qty
        delivered, outstanding = req["delivered"] + qty, req["outstanding"] - qty
        _bump(
            state,
            req,
            delivered=delivered,
            outstanding=outstanding,
            status="fulfilled" if not outstanding else req["status"],
        )
        _changed(state, req, "fulfilled" if not outstanding else "delivered")
    else:
        raise BankFault(404, "not_found", "No such action")
    return req


# ------------------------------------------------------------------- imports


def add_parts(state: FakeBankState, imp: _Import, text: str) -> dict[str, Any]:
    for part in read_parts(text):
        if imp.export is None:
            imp.export, imp.total, imp.crc = part.export, part.total, part.crc
        elif (part.export, part.total, part.crc) != (imp.export, imp.total, imp.crc):
            raise _transport_error("mixed_exports")
        if imp.parts.get(part.n, part.data) != part.data:
            raise _transport_error("conflicting_part")
        imp.parts[part.n] = part.data
    missing = [n for n in range(1, imp.total + 1) if n not in imp.parts]
    if imp.export is not None and not missing and imp.snapshot is None:
        try:
            payload = b"".join(base64.b64decode(imp.parts[n], validate=True) for n in range(1, imp.total + 1))
        except (binascii.Error, ValueError):
            raise _transport_error("bad_base64") from None
        if len(payload) > MAX_BYTES:
            raise _transport_error("too_large")
        if f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}" != imp.crc:
            raise _transport_error("crc_mismatch")
        try:
            imp.snapshot = json.loads(payload)
        except ValueError:
            raise BankFault(
                422, "invalid_snapshot", "The export is not a snapshot", details={"issues": ["json"]}
            ) from None
    return {
        "exportId": imp.export,
        "received": sorted(imp.parts),
        "total": imp.total,
        "missing": missing,
        "complete": imp.snapshot is not None,
    }


def _matched(state: FakeBankState, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    key = tuple(str(snapshot["source"].get(k, "")).lower() for k in ("guild", "realm", "region"))
    return next(
        (s for s in state.sources.values() if tuple(s[k].lower() for k in ("guild", "realm", "region")) == key), None
    )


def preview(state: FakeBankState, imp: _Import) -> dict[str, Any]:
    snap = imp.snapshot
    if snap is None:
        raise BankFault(422, "incomplete", "Some parts are still missing")
    matched = _matched(state, snap)
    receipt = state.receipts.get(snap["snapshotId"])
    return {
        "snapshotId": snap["snapshotId"],
        "source": {k: snap["source"].get(k) for k in ("guild", "realm", "region")},
        "matchedSource": {"id": matched["id"], "name": matched["name"]} if matched else None,
        "uploader": snap.get("uploader"),
        "client": snap.get("client"),
        "capturedAt": snap.get("capturedAt"),
        "completedAt": snap.get("completedAt"),
        "stable": snap.get("stable", True),
        "tabs": [
            {
                "index": t["index"],
                "name": t.get("name"),
                "status": t.get("status", "observed"),
                "occupied": len(t.get("slots", [])),
                "items": len({s["itemId"] for s in t.get("slots", [])}),
                "olderThanBaseline": False,
            }
            for t in snap.get("tabs", [])
        ],
        "warnings": [
            f"tab {t['index']} was not readable" for t in snap.get("tabs", []) if t.get("status") != "observed"
        ],
        "existingReceipt": receipt[1] if receipt else None,
    }


def accept(state: FakeBankState, who: Who, imp: _Import) -> dict[str, Any]:
    snap = imp.snapshot
    if snap is None:
        raise BankFault(422, "incomplete", "Some parts are still missing")
    digest = hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest()
    earlier = state.receipts.get(snap["snapshotId"])
    if earlier is not None:
        if earlier[0] != digest:
            raise BankFault(409, "snapshot_conflict", "A different snapshot with this id was already accepted")
        return {**earlier[1], "duplicate": True}
    source = _matched(state, snap)
    if source is None:
        if not who.admin:
            raise BankFault(422, "unknown_source", "This bank is not registered; ask a global officer to accept it")
        source = state.add_source(
            name=f"{snap['source']['guild']} bank",
            managers=[who.member],
            **{k: snap["source"][k] for k in ("guild", "realm", "region")},
        )
    elif not (who.manages(source) or "officer" in who.roles):
        raise BankFault(403, "forbidden", "Only this bank's managers and officers can accept its snapshots")
    tabs = snap.get("tabs", [])
    receipt = {
        "snapshotId": snap["snapshotId"],
        "sourceId": source["id"],
        "acceptedAt": state.now(),
        "tabsUpdated": [t["index"] for t in tabs if t.get("status", "observed") == "observed"],
        "tabsKeptAsHistory": [],
        "tabsNotRead": [t["index"] for t in tabs if t.get("status", "observed") != "observed"],
        "duplicate": False,
    }
    state.store_snapshot(source["id"], snap)
    state.receipts[snap["snapshotId"]] = (digest, receipt)
    state.emit(
        "snapshot.accepted",
        {"source": _source_view(state, source), "receipt": receipt, "uploader": snap.get("uploader")},
    )
    return receipt


# ------------------------------------------------------------------------ app


def _who(request: Request, state: FakeBankState) -> Who:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), state.token.encode()):
        raise BankFault(401, "unauthorised", "Not the hub")
    member = request.headers.get("x-toads-member", "")
    if not member.isdigit():
        raise BankFault(400, "bad_request", "X-Toads-Member is required")
    roles = frozenset(r.strip() for r in request.headers.get("x-toads-roles", "").split(",") if r.strip())
    return Who(member, unquote(request.headers.get("x-toads-name", "")), roles)


def create_fake_bank(state: FakeBankState) -> FastAPI:
    app = FastAPI(title="Fake ToadsBank", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.fake = state

    @app.exception_handler(BankFault)
    async def _fault(_: Request, exc: BankFault) -> JSONResponse:
        error: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.details is not None:
            error["details"] = exc.details
        if exc.current is not None:
            error["current"] = exc.current
        return JSONResponse({"error": error}, status_code=exc.status)

    async def _deliver(start: int) -> None:
        if not state.events_url:
            return
        async with httpx.AsyncClient(timeout=5.0, transport=state.events_transport) as http:
            for event in state.events[start:]:
                try:
                    await http.post(state.events_url, json=event, headers={"Authorization": f"Bearer {state.token}"})
                except httpx.HTTPError:
                    # The real worker retries for a day; the fake keeps the event in state.events and moves on.
                    log.warning("fake bank could not deliver event %s", event["id"])

    async def _once(request: Request, who: Who, run: Callable[[], Any], status: int = 200) -> JSONResponse:
        """Idempotency-Key: a repeat returns the first answer; a different body under the same key is a conflict."""
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 128:
            raise BankFault(400, "bad_request", "Idempotency-Key is required")
        body = hashlib.sha256(await request.body()).hexdigest()
        seen = state.idempotency.get(f"{who.member}:{key}")
        if seen is not None:
            if seen[0] != body:
                raise BankFault(409, "idempotency_conflict", "This key was used for a different request")
            return JSONResponse(seen[2], status_code=seen[1])
        start = len(state.events)
        result = run()
        state.idempotency[f"{who.member}:{key}"] = (body, status, result)
        await _deliver(start)
        return JSONResponse(result, status_code=status)

    def _import(who: Who, import_id: str) -> _Import:
        imp = state.imports.get(import_id)
        if imp is None or imp.member != who.member:
            raise BankFault(404, "not_found", "No such import")
        if state.now() - imp.opened_at > SESSION_SECONDS:
            raise BankFault(422, "import_expired", "This import session expired; start again")
        return imp

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/v1/imports")
    async def open_import(request: Request) -> JSONResponse:
        who = _who(request, state)

        def run() -> dict[str, Any]:
            imp = _Import(state.next_id("imp"), who.member, state.now())
            state.imports[imp.id] = imp
            return {"id": imp.id, "openedAt": imp.opened_at, "expiresAt": imp.opened_at + SESSION_SECONDS}

        return await _once(request, who, run, 201)

    @app.post("/v1/imports/{import_id}/parts")
    async def parts(import_id: str, request: Request) -> JSONResponse:
        who = _who(request, state)
        text = str((await request.json()).get("text") or "")
        return await _once(request, who, lambda: add_parts(state, _import(who, import_id), text))

    @app.get("/v1/imports/{import_id}/preview")
    async def get_preview(import_id: str, request: Request) -> dict[str, Any]:
        who = _who(request, state)
        return preview(state, _import(who, import_id))

    @app.post("/v1/imports/{import_id}/accept")
    async def post_accept(import_id: str, request: Request) -> JSONResponse:
        who = _who(request, state)
        return await _once(request, who, lambda: accept(state, who, _import(who, import_id)))

    @app.get("/v1/sources")
    async def list_sources(request: Request) -> list[dict[str, Any]]:
        who = _who(request, state)
        return [_source_view(state, s) for s in _visible(state, who)]

    @app.post("/v1/sources")
    async def create_source(request: Request) -> JSONResponse:
        who = _who(request, state)
        if not who.admin:
            raise BankFault(403, "forbidden", "Only admins register sources")
        body = await request.json()
        return await _once(request, who, lambda: _source_view(state, state.add_source(**body)), 201)

    @app.patch("/v1/sources/{source_id}")
    async def patch_source(source_id: str, request: Request) -> JSONResponse:
        who = _who(request, state)
        source = state.sources.get(source_id)
        if not who.admin or source is None:
            raise BankFault(403 if source else 404, "forbidden" if source else "not_found", "Not allowed")
        body = await request.json()

        def run() -> dict[str, Any]:
            if body.get("expectedRevision") != source["revision"]:
                raise BankFault(409, "stale_revision", "The source changed", current=_source_view(state, source))
            source.update({k: v for k, v in body.items() if k in ("name", "audience", "raidDay", "managers")})
            source["revision"] += 1
            return _source_view(state, source)

        return await _once(request, who, run)

    @app.get("/v1/sources/{source_id}/replica")
    async def replica(source_id: str, request: Request) -> dict[str, Any]:
        who = _who(request, state)
        source = state.sources.get(source_id)
        if source is None or not who.sees(source):
            raise BankFault(404, "not_found", "No such source")
        tabs = [
            {
                **{k: t.get(k) for k in ("index", "name", "status", "observedAt", "capacity")},
                "slots": [{**s, "name": _item_name(s)} for s in t.get("slots", [])],
            }
            for t in state.snapshots.get(source_id, {}).get("tabs", [])
        ]
        return {"source": _source_view(state, source), "tabs": tabs}

    @app.get("/v1/inventory")
    async def get_inventory(request: Request) -> dict[str, Any]:
        who = _who(request, state)
        q = request.query_params
        return inventory(state, who, q.get("q", ""), q.get("sourceId", ""))

    @app.post("/v1/requests")
    async def post_request(request: Request) -> JSONResponse:
        who = _who(request, state)
        body = await request.json()
        return await _once(request, who, lambda: dict(create_request(state, who, body)), 201)

    @app.get("/v1/requests")
    async def list_requests(request: Request) -> list[dict[str, Any]]:
        who = _who(request, state)
        scope, status = request.query_params.get("scope", "mine"), request.query_params.get("status")
        rows = list(state.requests.values())
        if scope == "mine":
            rows = [r for r in rows if r["memberId"] == who.member]
        elif scope == "queue":
            rows = [r for r in rows if who.manages(state.sources[r["sourceId"]]) and r["status"] in OPEN]
        elif not who.admin:
            rows = [r for r in rows if who.manages(state.sources[r["sourceId"]])]
        return sorted((r for r in rows if not status or r["status"] == status), key=lambda r: -r["createdAt"])

    @app.post("/v1/requests/{request_id}/{action}")
    async def request_action(request_id: str, action: str, request: Request) -> JSONResponse:
        who = _who(request, state)
        body = await request.json()
        return await _once(request, who, lambda: dict(act(state, who, request_id, action, body)))

    return app


# ---------------------------------------------------------------------- dev


def sample_snapshot(captured_at: int, snapshot_id: str = "spineshatter-bankalt-dev-0001") -> dict[str, Any]:
    """A small guild bank in the snapshot schema's shape, for the dev seed and tests."""

    def slot(n: int, item_id: int, name: str, count: int) -> dict[str, Any]:
        return {
            "slot": n,
            "itemId": item_id,
            "count": count,
            "link": f"|cffffffff|Hitem:{item_id}::::::::70:::::|h[{name}]|h|r",
        }

    return {
        "schema": "toadsbank.snapshot",
        "schemaVersion": 1,
        "snapshotId": snapshot_id,
        "addon": {"version": "0.1.0"},
        "client": {"flavour": "forever", "build": "0.0.0", "interface": 0},
        "source": {"kind": "guildBank", "guild": "Toads", "realm": "Spineshatter", "region": "EU"},
        "uploader": {"name": "Bankalt", "realm": "Spineshatter"},
        "capturedAt": captured_at,
        "completedAt": captured_at + 12,
        "stable": True,
        "tabs": [
            {
                "index": 1,
                "name": "Potions",
                "status": "observed",
                "capacity": 98,
                "observedAt": captured_at + 4,
                "slots": [
                    slot(1, 22832, "Super Mana Potion", 20),
                    slot(2, 22832, "Super Mana Potion", 20),
                    slot(3, 22829, "Super Healing Potion", 18),
                ],
            },
            {
                "index": 2,
                "name": "Flasks",
                "status": "observed",
                "capacity": 98,
                "observedAt": captured_at + 8,
                "slots": [
                    slot(1, 22854, "Flask of Relentless Assault", 15),
                    slot(2, 22861, "Flask of Blinding Light", 6),
                ],
            },
            {"index": 3, "name": "Officers", "status": "unknown", "capacity": 98, "observedAt": None, "slots": []},
        ],
    }


def seeded_state(manager: str = "1001", **kwargs: Any) -> FakeBankState:
    """One registered bank, captured an hour ago, managed by the dev user."""
    state = FakeBankState(**kwargs)
    source = state.add_source(
        name="Toads main bank", guild="Toads", realm="Spineshatter", region="EU", managers=[manager]
    )
    state.store_snapshot(source["id"], sample_snapshot(state.now() - 3600))
    return state


def app_from_env() -> FastAPI:
    """Entry point for the dev compose stack. Its token opens everything, so it needs an explicit opt-in."""
    if os.environ.get("FAKE_BANK_I_AM_DEV") != "1":
        raise RuntimeError("the fake bank is a development tool; set FAKE_BANK_I_AM_DEV=1, and only in the dev stack")
    return create_fake_bank(
        seeded_state(
            manager=os.environ.get("FAKE_BANK_MANAGER", "1001"),
            token=os.environ.get("FAKE_BANK_TOKEN", "replace-me"),
            events_url=os.environ.get("FAKE_BANK_EVENTS_URL", ""),
        )
    )
