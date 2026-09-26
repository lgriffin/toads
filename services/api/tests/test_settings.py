import pytest
from pydantic import ValidationError
from toads_api.settings import Settings


def test_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "REDIS_URL", "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "DISCORD_GUILD_ID"):
        monkeypatch.setenv(f"TOADS_{name}", "1")
    monkeypatch.delenv("TOADS_PUBLIC_BASE_URL", raising=False)
    with pytest.raises(ValidationError, match="public_base_url"):
        Settings()


@pytest.mark.security
def test_secrets_are_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "REDIS_URL", "DISCORD_CLIENT_ID", "DISCORD_GUILD_ID", "PUBLIC_BASE_URL"):
        monkeypatch.setenv(f"TOADS_{name}", "1")
    monkeypatch.setenv("TOADS_DISCORD_CLIENT_SECRET", "planted-secret-value")
    assert "planted-secret-value" not in repr(Settings())
