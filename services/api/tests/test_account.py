"""Member settings: the rules in AccountService, and the /api/me settings routes."""

from __future__ import annotations

import secrets
import uuid

import pytest
from toads_api.account.repository import InMemoryAccountRepository, MemberNames
from toads_api.account.service import AccountError, AccountService, NameSource

from conftest import Hub


def _service() -> AccountService:
    repo = InMemoryAccountRepository(
        members={
            1: MemberNames(1, 101, "Hops", "discord", None, {7: "Ribbit", 8: "Croak"}),
            2: MemberNames(2, 102, "Zed", "discord", None, {}),
        }
    )
    return AccountService(repo)


def test_discord_name_by_default() -> None:
    s = _service().settings(1)
    assert (s.shown_name, s.name_source, s.name_character_id) == ("Hops", NameSource.DISCORD, None)
    assert [o.name for o in s.name_options] == ["Hops", "Croak", "Ribbit"]
    assert s.wcl_key is None


def test_choose_an_approved_character() -> None:
    svc = _service()
    s = svc.choose_name(1, NameSource.CHARACTER, 7)
    assert (s.shown_name, s.name_source, s.name_character_id) == ("Ribbit", NameSource.CHARACTER, 7)
    assert [e.shown_name for e in svc.directory()] == ["Ribbit", "Zed"]
    assert svc.choose_name(1, NameSource.DISCORD, 7).shown_name == "Hops"


@pytest.mark.parametrize("character_id", [None, 99])
def test_only_approved_characters(character_id: int | None) -> None:
    with pytest.raises(AccountError) as info:
        _service().choose_name(1, NameSource.CHARACTER, character_id)
    assert info.value.status == 422


def test_lost_claim_falls_back_to_discord_name() -> None:
    svc = _service()
    svc.choose_name(1, NameSource.CHARACTER, 7)
    assert isinstance(svc.repo, InMemoryAccountRepository)
    m = svc.repo.members[1]
    svc.repo.members[1] = MemberNames(1, 101, "Hops", m.name_source, m.name_character_id, {8: "Croak"})
    s = svc.settings(1)
    assert (s.shown_name, s.name_source, s.name_character_id) == ("Hops", NameSource.DISCORD, None)


@pytest.mark.security
@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [("short", "long-enough-secret"), ("has spaces in it", "long-enough-secret"), (str(uuid.uuid4()), "tiny")],
)
def test_malformed_keys_are_refused(client_id: str, client_secret: str) -> None:
    with pytest.raises(AccountError) as info:
        _service().save_wcl_key(1, client_id, client_secret)
    assert info.value.status == 422
    assert client_secret not in info.value.message


def test_save_and_remove_key() -> None:
    svc = _service()
    cid = str(uuid.uuid4())
    s = svc.save_wcl_key(1, f"  {cid} ", secrets.token_urlsafe(30))
    assert s.wcl_key is not None and s.wcl_key.client_id_hint == cid[-4:] and s.wcl_key.status == "unverified"
    assert svc.remove_wcl_key(1).wcl_key is None


def test_unknown_member() -> None:
    with pytest.raises(AccountError) as info:
        _service().settings(3)
    assert info.value.status == 404


def test_routes_need_a_session(hub: Hub) -> None:
    assert hub.get("/api/me/settings", None).status_code == 401
    assert hub.client.put("/api/me/name", json={"source": "discord"}).status_code == 401
    assert hub.client.put("/api/me/wcl-key", json={"client_id": "x", "client_secret": "y"}).status_code == 401
    assert hub.delete("/api/me/wcl-key", None).status_code == 401


@pytest.mark.security
def test_plain_member_can_manage_own_settings(hub: Hub) -> None:
    sid = hub.login(hub.user(nick="Visitor"))
    s = hub.get("/api/me/settings", sid).json()
    assert (s["shown_name"], s["wcl_key"], s["wcl_key_in_use"]) == ("Visitor", None, "guild")
    secret = secrets.token_urlsafe(30)
    r = hub.client.put(
        "/api/me/wcl-key", headers=hub.as_(sid), json={"client_id": str(uuid.uuid4()), "client_secret": secret}
    )
    assert r.status_code == 200 and r.json()["wcl_key_in_use"] == "own"
    assert secret not in r.text


@pytest.mark.security
def test_rejected_key_is_not_echoed(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    secret = "not a secret with spaces " + secrets.token_urlsafe(8)
    r = hub.client.put(
        "/api/me/wcl-key", headers=hub.as_(sid), json={"client_id": str(uuid.uuid4()), "client_secret": secret}
    )
    assert r.status_code == 422
    assert secret not in r.text
