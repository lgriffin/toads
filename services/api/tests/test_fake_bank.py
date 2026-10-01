"""The fake ToadsBank itself: enough of the v1 contract that the hub's tests and the dev stack can trust it."""

from __future__ import annotations

import base64
import json
import zlib
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from toads_api.testing import fake_bank
from toads_api.testing.fake_bank import FakeBankState, create_fake_bank, encode_parts, sample_snapshot, seeded_state

TOKEN = "-".join(("fake", "bank", "token"))
NOW = 1_000_000


class Bank:
    def __init__(self, **kwargs: Any) -> None:
        self.state: FakeBankState = seeded_state(manager="7", token=TOKEN, clock=lambda: NOW, **kwargs)
        self.client = TestClient(create_fake_bank(self.state))
        self.keys = 0

    def headers(self, member: str = "7", roles: str = "member,officer", key: bool = True) -> dict[str, str]:
        self.keys += 1
        h = {"Authorization": f"Bearer {TOKEN}", "X-Toads-Member": member, "X-Toads-Roles": roles}
        return {**h, "Idempotency-Key": f"k{self.keys}"} if key else h

    def post(self, path: str, body: Any = None, **who: Any) -> httpx.Response:
        return self.client.post(f"/v1{path}", json=body or {}, headers=self.headers(**who))

    def get(self, path: str, **who: Any) -> httpx.Response:
        return self.client.get(f"/v1{path}", headers=self.headers(key=False, **who))

    def open(self, **who: Any) -> str:
        return str(self.post("/imports", **who).json()["id"])


@pytest.fixture
def bank() -> Bank:
    return Bank()


def _code(r: httpx.Response) -> tuple[int, str]:
    return r.status_code, r.json()["error"]["code"]


def test_health_and_auth(bank: Bank) -> None:
    assert bank.client.get("/health").json() == {"ok": True}
    assert _code(bank.client.get("/v1/sources")) == (401, "unauthorised")
    no_member = {"Authorization": f"Bearer {TOKEN}"}
    assert _code(bank.client.get("/v1/sources", headers=no_member)) == (400, "bad_request")
    assert _code(bank.client.post("/v1/imports", json={}, headers=bank.headers(key=False))) == (400, "bad_request")


def _part(export: str, n: int, total: int, crc: str, data: str) -> str:
    return f"TOADSBANK/1 export={export} part={n}/{total} crc32={crc}\n{data}"


def _payload(text: str) -> tuple[str, str]:
    raw = text.encode()
    return f"{zlib.crc32(raw) & 0xFFFFFFFF:08x}", base64.b64encode(raw).decode()


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("TOADSBANK/1 export=bad!id part=1/1 crc32=00000000", "bad_header"),
        ("TOADSBANK/2 export=abcdefgh part=1/1 crc32=00000000", "unsupported_version"),
        ("TOADSBANK/1 export=abcdefgh part=3/2 crc32=00000000", "bad_part_number"),
        ("TOADSBANK/1 export=abcdefgh part=1/801 crc32=00000000", "too_many_parts"),
        (
            _part("abcdefgh", 1, 2, "00000000", "AAAA") + "\n" + _part("other-id", 2, 2, "00000000", "AAAA"),
            "mixed_exports",
        ),
        (
            _part("abcdefgh", 1, 2, "00000000", "AAAA") + "\n" + _part("abcdefgh", 1, 2, "00000000", "BBBB"),
            "conflicting_part",
        ),
        (_part("abcdefgh", 1, 1, "00000000", base64.b64encode(b"{}").decode()), "crc_mismatch"),
        (_part("abcdefgh", 1, 1, "00000000", "@@@@"), "bad_base64"),
    ],
)
def test_the_reader_refuses_broken_pastes(bank: Bank, text: str, code: str) -> None:
    r = bank.post(f"/imports/{bank.open()}/parts", {"text": text})
    assert _code(r) == (422, "transport_error")
    assert r.json()["error"]["details"] == {"code": code}


def test_a_payload_that_is_not_json_is_an_invalid_snapshot(bank: Bank) -> None:
    crc, data = _payload("not json")
    r = bank.post(f"/imports/{bank.open()}/parts", {"text": _part("abcdefgh", 1, 1, crc, data)})
    assert _code(r) == (422, "invalid_snapshot")


def test_imports_belong_to_their_member_and_expire(bank: Bank) -> None:
    import_id = bank.open()
    assert _code(bank.get(f"/imports/{import_id}/preview", member="8")) == (404, "not_found")
    bank.state.clock = lambda: NOW + 31 * 60
    assert _code(bank.get(f"/imports/{import_id}/preview")) == (422, "import_expired")


def _import(bank: Bank, snapshot: dict[str, Any], **who: Any) -> str:
    import_id = bank.open(**who)
    progress = bank.post(f"/imports/{import_id}/parts", {"text": "\n\n".join(encode_parts(snapshot))}, **who).json()
    assert progress["complete"], progress
    return import_id


def test_an_unknown_bank_needs_an_admin_who_then_registers_it(bank: Bank) -> None:
    snapshot = sample_snapshot(NOW - 60, "otherrealm-alt-0001")
    snapshot["source"]["guild"] = "Toads Alts"
    import_id = _import(bank, snapshot)
    assert bank.get(f"/imports/{import_id}/preview").json()["matchedSource"] is None
    assert _code(bank.post(f"/imports/{import_id}/accept")) == (422, "unknown_source")
    receipt = bank.post(f"/imports/{import_id}/accept", roles="member,officer,admin").json()
    source = bank.state.sources[receipt["sourceId"]]
    assert (source["guild"], source["managers"]) == ("Toads Alts", ["7"])


def test_a_snapshot_id_is_accepted_once(bank: Bank) -> None:
    snapshot = sample_snapshot(NOW - 60, "spineshatter-bankalt-0009")
    first = bank.post(f"/imports/{_import(bank, snapshot)}/accept").json()
    again = bank.post(f"/imports/{_import(bank, snapshot)}/accept").json()
    assert (first["duplicate"], again["duplicate"]) == (False, True)
    preview = bank.get(f"/imports/{_import(bank, snapshot)}/preview").json()
    assert preview["existingReceipt"]["snapshotId"] == "spineshatter-bankalt-0009"
    snapshot["tabs"][0]["slots"][0]["count"] = 1
    assert _code(bank.post(f"/imports/{_import(bank, snapshot)}/accept")) == (409, "snapshot_conflict")
    stranger = _import(bank, sample_snapshot(NOW - 60, "spineshatter-bankalt-0010"), member="9", roles="member")
    assert _code(bank.post(f"/imports/{stranger}/accept", member="9", roles="member")) == (403, "forbidden")


def test_events_go_to_the_hub_with_the_token() -> None:
    seen: list[tuple[str, dict[str, Any]]] = []

    def hub(request: httpx.Request) -> httpx.Response:
        seen.append((request.headers["Authorization"], json.loads(request.content)))
        return httpx.Response(200 if len(seen) == 1 else 503)

    bank = Bank(events_url="http://hub.test/api/bank/events", events_transport=httpx.MockTransport(hub))
    body = {"sourceId": "src_1", "itemId": 22832, "quantity": 1, "character": "Frog"}
    assert bank.post("/requests", body, member="9", roles="member").status_code == 201
    assert [e["type"] for _, e in seen] == ["request.created", "request.assigned"]
    assert seen[0][0] == f"Bearer {TOKEN}"

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    bank.state.events_transport = httpx.MockTransport(down)
    assert bank.post("/requests", body, member="9", roles="member").status_code == 201
    assert len(bank.state.events) == 4  # kept, though the hub never heard them


def test_sources_are_admin_work(bank: Bank) -> None:
    body = {"name": "Alts", "guild": "Toads Alts", "realm": "Spineshatter", "region": "EU", "managers": []}
    assert _code(bank.post("/sources", body)) == (403, "forbidden")
    created = bank.post("/sources", body, roles="member,officer,admin").json()
    patch = bank.client.patch(
        f"/v1/sources/{created['id']}", json={"expectedRevision": 0}, headers=bank.headers(roles="member,admin")
    )
    assert _code(patch) == (409, "stale_revision")
    assert patch.json()["error"]["current"]["revision"] == 1
    missing = bank.client.patch("/v1/sources/src_404", json={}, headers=bank.headers(roles="member,admin"))
    assert _code(missing) == (404, "not_found")
    assert _code(bank.get("/sources/src_404/replica")) == (404, "not_found")


def test_request_rules(bank: Bank) -> None:
    member = {"member": "9", "roles": "member"}
    assert _code(bank.post("/requests", {"sourceId": "src_404", "itemId": 1, "quantity": 1, "character": "x"})) == (
        404,
        "not_found",
    )
    assert _code(bank.post("/requests", {"sourceId": "src_1", "itemId": 1, "quantity": 0, "character": "x"})) == (
        400,
        "validation_failed",
    )
    assert _code(bank.post("/requests", {"sourceId": "src_1", "itemId": 1, "quantity": 1, "character": "x"})) == (
        404,
        "not_found",
    )
    req = bank.post("/requests", {"sourceId": "src_1", "itemId": 22829, "quantity": 2, "character": "x"}, **member)
    created = req.json()
    assert _code(bank.post(f"/requests/{created['id']}/approve", {"expectedRevision": 1}, **member)) == (
        403,
        "forbidden",
    )
    assert _code(bank.post("/requests/req_404/approve", {"expectedRevision": 1})) == (404, "not_found")
    assert _code(bank.post(f"/requests/{created['id']}/teleport", {"expectedRevision": 1})) == (404, "not_found")
    too_many = bank.post(f"/requests/{created['id']}/deliveries", {"expectedRevision": 1, "quantity": 5})
    assert _code(too_many) == (409, "over_allocated")
    done = bank.post(f"/requests/{created['id']}/deliveries", {"expectedRevision": 1, "quantity": 2}).json()
    assert (done["status"], done["outstanding"]) == ("fulfilled", 0)
    assert _code(bank.post(f"/requests/{done['id']}/cancel", {"expectedRevision": 2}, **member)) == (
        409,
        "invalid_transition",
    )
    assert [r["id"] for r in bank.get("/requests?scope=all").json()] == [created["id"]]
    assert bank.get("/requests?scope=all", member="9", roles="member").json() == []
    assert [r["status"] for r in bank.get("/requests?scope=mine&status=fulfilled", **member).json()] == ["fulfilled"]
    assert bank.get("/requests?scope=queue").json() == []


def test_officers_only_banks_are_hidden_from_members(bank: Bank) -> None:
    bank.state.sources["src_1"]["audience"] = "officers"
    assert bank.get("/sources", member="9", roles="member").json() == []
    assert bank.get("/inventory", member="9", roles="member").json() == {"range": None, "items": []}
    assert len(bank.get("/sources").json()) == 1


def test_the_dev_entry_point_needs_an_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FAKE_BANK_I_AM_DEV", raising=False)
    with pytest.raises(RuntimeError, match="FAKE_BANK_I_AM_DEV"):
        fake_bank.app_from_env()
    monkeypatch.setenv("FAKE_BANK_I_AM_DEV", "1")
    monkeypatch.setenv("FAKE_BANK_MANAGER", "1001")
    app = fake_bank.app_from_env()
    assert app.title == "Fake ToadsBank"
    assert app.state.fake.sources["src_1"]["managers"] == ["1001"]
