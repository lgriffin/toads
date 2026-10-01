import pytest
from pydantic import ValidationError
from toads_api.settings import Settings

REQUIRED = (
    "DATABASE_URL",
    "REDIS_URL",
    "DISCORD_CLIENT_ID",
    "DISCORD_CLIENT_SECRET",
    "DISCORD_BOT_TOKEN",
    "DISCORD_GUILD_ID",
    "DISCORD_REDIRECT_URI",
    "PUBLIC_BASE_URL",
    "HUB_SERVICE_TOKEN",
    "CREDENTIALS_KEYS",
)


def _env(monkeypatch: pytest.MonkeyPatch, *, skip: str = "") -> None:
    for name in REQUIRED:
        if name != skip:
            monkeypatch.setenv(f"TOADS_{name}", "1")
    if skip:
        monkeypatch.delenv(f"TOADS_{skip}", raising=False)


@pytest.mark.parametrize("name", REQUIRED)
def test_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    _env(monkeypatch, skip=name)
    with pytest.raises(ValidationError, match=name.lower()):
        Settings()


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    s = Settings()
    assert s.session_ttl_seconds == 7 * 24 * 3600
    assert s.role_refresh_seconds == 15 * 60
    assert s.discord_api_base == "https://discord.com/api/v10"


def test_role_refresh_cannot_exceed_15_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    monkeypatch.setenv("TOADS_ROLE_REFRESH_SECONDS", str(15 * 60 + 1))
    with pytest.raises(ValidationError, match="role_refresh_seconds"):
        Settings()


def test_bank_is_off_by_default_and_blank_channels_mean_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    monkeypatch.setenv("TOADS_BANK_CHANNEL_ID", "")
    monkeypatch.setenv("TOADS_BANK_FALLBACK_CHANNEL_ID", "42")
    s = Settings()
    assert (s.bank_url, s.bank_service_token.get_secret_value()) == ("", "")
    assert (s.bank_channel_id, s.bank_fallback_channel_id) == (None, 42)


@pytest.mark.security
@pytest.mark.parametrize(
    "secret",
    [
        "DISCORD_CLIENT_SECRET",
        "DISCORD_BOT_TOKEN",
        "DATABASE_URL",
        "HUB_SERVICE_TOKEN",
        "CREDENTIALS_KEYS",
        "BANK_SERVICE_TOKEN",
    ],
)
def test_secrets_are_not_in_repr(monkeypatch: pytest.MonkeyPatch, secret: str) -> None:
    _env(monkeypatch)
    monkeypatch.setenv(f"TOADS_{secret}", "planted-secret-value")
    assert "planted-secret-value" not in repr(Settings())


def test_env_example_lists_every_setting() -> None:
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / ".env.example"
    names = {line.split("=", 1)[0] for line in example.read_text().splitlines() if "=" in line and line[0] != "#"}
    assert names == {f"TOADS_{f.upper()}" for f in Settings.model_fields}


@pytest.mark.security
def test_env_example_secrets_are_placeholders() -> None:
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / ".env.example"
    values = dict(line.split("=", 1) for line in example.read_text().splitlines() if "=" in line and line[0] != "#")
    for name in (
        "TOADS_DISCORD_CLIENT_SECRET",
        "TOADS_DISCORD_BOT_TOKEN",
        "TOADS_CREDENTIALS_KEYS",
        "TOADS_BANK_SERVICE_TOKEN",
    ):
        assert values[name] == "replace-me"
