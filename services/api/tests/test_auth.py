"""Discord OAuth2 + PKCE login, sessions and role refresh (REQ-HUB-AUTH-001/002, REQ-HUB-RBAC-002)."""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

import pytest
from hub_db import Member
from sqlalchemy import func, select
from toads_api.sessions import LOGIN_COOKIE, SESSION_COOKIE

from conftest import HUB, Hub


def _set_cookie(response, name: str) -> str:
    return next(h for h in response.headers.get_list("set-cookie") if h.startswith(f"{name}="))


def test_login_redirects_to_discord_with_pkce(hub: Hub) -> None:
    r = hub.start_login()
    assert r.status_code == 302
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["toads-dev"]
    assert q["redirect_uri"] == [f"{HUB}/auth/callback"]
    assert q["code_challenge_method"] == ["S256"]
    assert len(q["code_challenge"][0]) == 43
    assert len(q["state"][0]) >= 32
    assert "guilds.members.read" in q["scope"][0]


@pytest.mark.security
def test_login_cookie_is_httponly_secure_lax_and_scoped(hub: Hub) -> None:
    header = _set_cookie(hub.start_login(), LOGIN_COOKIE).lower()
    for flag in ("httponly", "secure", "samesite=lax", "path=/auth", "max-age=600"):
        assert flag in header


@pytest.mark.security
def test_member_gets_secure_session(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Hopscotch")
    r = hub.callback(hub.authorize(hub.start_login(), user))
    assert r.status_code == 303
    assert r.headers["location"] == f"{HUB}/hub"
    header = _set_cookie(r, SESSION_COOKIE).lower()
    for flag in ("httponly", "secure", "samesite=lax", "path=/", f"max-age={7 * 24 * 3600}"):
        assert flag in header
    session_id = r.cookies[SESSION_COOKIE]
    hub.client.cookies.clear()
    info = hub.get("/api/session", session_id).json()
    assert info["display_name"] == "Hopscotch"
    assert info["day_roles"] == {"wed": "raider"}
    assert info["global_officer"] is False


@pytest.mark.security
def test_session_is_stored_hashed_with_ttl(hub: Hub) -> None:
    session_id = hub.login(hub.user(("wed", "raider")))

    async def keys() -> list[bytes]:
        return [k async for k in hub.redis.scan_iter("toads:session:*")]

    found = hub.client.portal.call(keys)
    assert len(found) == 1
    assert session_id.encode() not in found[0]
    ttl = hub.client.portal.call(hub.redis.ttl, found[0])
    assert 0 < ttl <= 7 * 24 * 3600


@pytest.mark.security
def test_replayed_state_is_refused(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    login = hub.start_login()
    callback = hub.authorize(login, user)
    assert hub.callback(callback).status_code == 303
    # Replay the same callback with the same pre-auth cookie: the pending login was consumed.
    hub.client.cookies.set(LOGIN_COOKIE, login.cookies[LOGIN_COOKIE], domain="hub.test", path="/auth")
    hub.client.cookies.delete(SESSION_COOKIE)
    replay = hub.callback(callback)
    assert replay.status_code == 400
    assert SESSION_COOKIE not in replay.cookies


@pytest.mark.security
def test_state_must_match_the_login_cookie(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    first = hub.start_login()
    hub.start_login()  # a second login replaces the pre-auth cookie in this browser
    r = hub.callback(hub.authorize(first, user))  # state from the first login, cookie from the second
    assert r.status_code == 400
    assert SESSION_COOKIE not in r.cookies


@pytest.mark.security
def test_callback_without_login_cookie_is_refused(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    callback = hub.authorize(hub.start_login(), user)
    hub.client.cookies.clear()
    assert hub.callback(callback).status_code == 400


@pytest.mark.security
def test_pkce_mismatch_is_refused(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    login = hub.start_login()
    location = login.headers["location"]
    # A code issued for a different challenge (e.g. intercepted from another login) cannot be redeemed.
    wrong = location.replace("code_challenge=", "code_challenge=x")
    callback = hub.discord.get(
        f"{wrong.removeprefix('https://discord.test')}&login_as={user.user_id}", follow_redirects=False
    ).headers["location"]
    r = hub.callback(callback)
    assert r.status_code == 400
    assert SESSION_COOKIE not in r.cookies


def test_challenge_is_s256_of_a_valid_verifier() -> None:
    from toads_api.auth import pkce_challenge

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert pkce_challenge(verifier) == expected == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_cancelled_sign_in(hub: Hub) -> None:
    login = hub.start_login()
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    r = hub.client.get("/auth/callback", params={"state": state, "error": "access_denied"}, follow_redirects=False)
    assert r.status_code == 400


def test_non_member_gets_members_only_and_no_session(hub: Hub) -> None:
    stranger = hub.user(in_guild=False)
    r = hub.callback(hub.authorize(hub.start_login(), stranger))
    assert r.status_code == 303
    assert r.headers["location"] == f"{HUB}/members-only"
    assert SESSION_COOKIE not in r.cookies
    with hub.db() as db:
        assert db.scalar(select(func.count()).select_from(Member)) == 0


def test_login_upserts_member_and_rotates_session(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Hops")
    first = hub.login(user)
    user.nick = "Hopscotch"
    hub.client.cookies.set(SESSION_COOKIE, first, domain="hub.test")
    second = hub.callback(hub.authorize(hub.start_login(), user)).cookies[SESSION_COOKIE]
    hub.client.cookies.clear()
    assert second != first
    assert hub.get("/api/session", first).status_code == 401
    assert hub.get("/api/session", second).json()["display_name"] == "Hopscotch"
    with hub.db() as db:
        assert [m.display_name for m in db.scalars(select(Member))] == ["Hopscotch"]


def test_logout_ends_session(hub: Hub) -> None:
    session_id = hub.login(hub.user(("wed", "raider")))
    r = hub.client.post("/auth/logout", headers=hub.as_(session_id), follow_redirects=False)
    assert r.status_code == 303
    assert "max-age=0" in _set_cookie(r, SESSION_COOKIE).lower()
    assert hub.get("/api/session", session_id).status_code == 401


def test_unknown_session_is_401(hub: Hub) -> None:
    assert hub.get("/api/session", "made-up").status_code == 401
    assert hub.get("/api/session", None).status_code == 401


def test_rejected_client_secret_is_refused(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    callback = hub.authorize(hub.start_login(), user)
    hub.fake.client_secret = "rotated"  # noqa: S105 - token endpoint now answers 401
    assert hub.callback(callback).status_code == 400


def test_discord_down_at_callback_is_502(hub: Hub) -> None:
    from toads_api.discord_api import DiscordError

    user = hub.user(("wed", "raider"))
    callback = hub.authorize(hub.start_login(), user)

    async def down(code: str, verifier: str) -> str:
        raise DiscordError("HTTP 500")

    hub.services.discord.exchange_code = down
    r = hub.callback(callback)
    assert r.status_code == 502
    assert SESSION_COOKIE not in r.cookies


# --- role refresh (REQ-HUB-RBAC-002) ----------------------------------------------------------------


def test_roles_are_not_reread_before_the_interval(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    session_id = hub.login(user)
    user.roles.add(21)
    hub.pass_time(15 * 60 - 1)
    assert hub.get("/api/session", session_id).json()["day_roles"] == {"wed": "raider"}


def test_added_role_takes_effect_after_refresh(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    session_id = hub.login(user)
    user.roles.add(21)
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).json()["day_roles"] == {"wed": "raider", "sun": "raider"}


def test_removed_role_ends_session_on_refresh(hub: Hub) -> None:
    user = hub.user(("wed", "officer"), ("wed", "raider"))
    session_id = hub.login(user)
    user.roles.discard(12)
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).status_code == 401
    assert hub.get("/api/session", session_id).status_code == 401


def test_removed_unmapped_role_keeps_session(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    user.roles.add(12345)
    session_id = hub.login(user)
    user.roles.discard(12345)
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).status_code == 200


def test_leaving_the_server_ends_session(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    session_id = hub.login(user)
    user.in_guild = False
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).status_code == 401


def test_revoked_token_ends_session(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    session_id = hub.login(user)
    hub.fake.revoke_tokens(user.user_id)
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).status_code == 401


def test_discord_outage_on_refresh_fails_closed(hub: Hub) -> None:
    session_id = hub.login(hub.user(("wed", "officer")))

    async def boom(_: str) -> None:
        raise RuntimeError("discord down")

    hub.services.discord.current_member = boom
    hub.pass_time(15 * 60)
    assert hub.get("/api/session", session_id).status_code == 503


def test_session_expires_after_ttl(hub: Hub) -> None:
    session_id = hub.login(hub.user(("wed", "raider")))

    async def expire() -> None:
        async for key in hub.redis.scan_iter("toads:session:*"):
            await hub.redis.delete(key)

    hub.client.portal.call(expire)
    assert hub.get("/api/session", session_id).status_code == 401
