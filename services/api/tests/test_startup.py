"""Startup checks (REQ-HUB-DAY-022, REQ-DEV-CFG-001) and the Discord client's error handling."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from toads_api.discord_api import DiscordAuthError, DiscordError, HttpDiscord
from toads_api.main import create_app
from toads_api.rbac import RaidDaysConfig, UnknownDiscordRoleError
from toads_api.services import build_services
from toads_api.testing.fake_discord import FakeDiscordState, app_from_env

from conftest import RAID_DAYS, Hub, make_settings


def test_startup_passes_when_every_role_exists() -> None:
    hub = Hub()
    with hub.client:
        assert hub.client.get("/healthz").status_code == 200


def test_startup_fails_naming_day_and_role() -> None:
    cfg = RAID_DAYS.model_copy(deep=True)
    cfg.raid_days[1].officer_roles.append(424242)
    hub = Hub(raid_days=cfg)
    with pytest.raises(UnknownDiscordRoleError, match=r"raid day 'sun' officer role 424242"), hub.client:
        pass


def test_unknown_global_officer_role_is_named() -> None:
    cfg = RaidDaysConfig(global_officer_roles=[7])
    with pytest.raises(UnknownDiscordRoleError, match="global officers role 7"):
        cfg.check_roles_exist({1, 2})


def test_example_config_loads() -> None:
    cfg = RaidDaysConfig.load(Path(__file__).resolve().parents[3] / "config" / "raid_days.example.yaml")
    assert [d.id for d in cfg.raid_days] == ["wed", "sun"]
    cfg.check_roles_exist(set())


def test_missing_env_fails_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TOADS_DATABASE_URL", "TOADS_REDIS_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(Exception, match="database_url"), TestClient(create_app()):
        pass


@pytest.mark.anyio
async def test_build_services_from_settings(tmp_path: Path) -> None:
    cfg = tmp_path / "days.yaml"
    cfg.write_text("raid_days: [{id: wed, name: Wednesday}]\n")
    services = build_services(make_settings(raid_days_config=cfg, redis_url="redis://localhost:1/0"))
    assert [d.id for d in services.raid_days.raid_days] == ["wed"]
    assert services.characters.name_of(1) is None
    await services.aclose()


def _discord(handler: httpx.MockTransport) -> HttpDiscord:
    return HttpDiscord(
        httpx.AsyncClient(transport=handler),
        api_base="https://discord.test/api/v10/",
        client_id="c",
        client_secret=SecretStr("s"),
        bot_token=SecretStr("b"),
        redirect_uri="https://hub.test/auth/callback",
        guild_id=1,
    )


def _answer(status: int, body: object = None) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _: httpx.Response(status, json=body))


@pytest.mark.anyio
@pytest.mark.parametrize(("status", "body", "error"), [(400, {}, DiscordAuthError), (500, {}, DiscordError)])
async def test_token_exchange_errors(status: int, body: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        await _discord(_answer(status, body)).exchange_code("code", "verifier")


@pytest.mark.anyio
async def test_token_response_without_token() -> None:
    with pytest.raises(DiscordError, match="no access token"):
        await _discord(_answer(200, {"token_type": "Bearer"})).exchange_code("code", "verifier")


@pytest.mark.anyio
async def test_member_lookup_errors() -> None:
    with pytest.raises(DiscordAuthError):
        await _discord(_answer(401)).current_member("t")
    with pytest.raises(DiscordError):
        await _discord(_answer(502)).current_member("t")


@pytest.mark.anyio
async def test_role_listing_error() -> None:
    with pytest.raises(DiscordError, match="HTTP 403"):
        await _discord(_answer(403)).guild_role_ids()


@pytest.mark.anyio
@pytest.mark.security
async def test_errors_do_not_leak_tokens() -> None:
    try:
        await _discord(_answer(500, {"echo": "planted-secret-value"})).exchange_code("planted-secret-value", "v")
    except DiscordError as exc:
        assert "planted-secret-value" not in str(exc)


# --- the fake Discord itself -------------------------------------------------------------------------


def test_fake_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_DISCORD_ROLES", "11, 12")
    monkeypatch.setenv("FAKE_DISCORD_GUILD_ROLES", "99")
    monkeypatch.setenv("FAKE_DISCORD_NICK", "Hopscotch")
    state = FakeDiscordState.from_env()
    assert state.guild_roles == {11, 12, 99}
    assert state.login_as is not None
    assert state.users[state.login_as].nick == "Hopscotch"
    with pytest.raises(RuntimeError, match="FAKE_DISCORD_I_AM_DEV"):
        app_from_env()
    monkeypatch.setenv("FAKE_DISCORD_I_AM_DEV", "1")
    assert app_from_env().title == "Fake Discord"


@pytest.mark.parametrize(
    "query",
    [
        "client_id=wrong&response_type=code&code_challenge=x&code_challenge_method=S256&redirect_uri=https://h",
        "client_id=toads-dev&response_type=code&code_challenge=x&code_challenge_method=plain&redirect_uri=https://h",
        "client_id=toads-dev&response_type=code&code_challenge=x&code_challenge_method=S256",
    ],
)
def test_fake_authorize_rejects_bad_requests(hub: Hub, query: str) -> None:
    assert hub.discord.get(f"/oauth2/authorize?{query}", follow_redirects=False).status_code == 400


def test_fake_token_rejects_bad_grants(hub: Hub) -> None:
    form = {"client_id": "toads-dev", "client_secret": "replace-me", "grant_type": "refresh_token"}
    assert hub.discord.post("/api/v10/oauth2/token", data=form).json() == {"error": "unsupported_grant_type"}
    form["grant_type"] = "authorization_code"
    assert hub.discord.post("/api/v10/oauth2/token", data=form).json() == {"error": "invalid_grant"}


def test_fake_endpoints_need_tokens(hub: Hub) -> None:
    assert hub.discord.get("/api/v10/users/@me/guilds/77/member").status_code == 401
    assert hub.discord.get("/api/v10/guilds/77/roles").status_code == 401
    assert hub.discord.get("/api/v10/guilds/77/roles", headers={"authorization": "Bot x"}).status_code == 200
