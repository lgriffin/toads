import pytest
from toads_bot.__main__ import create_bot
from toads_bot.settings import Settings


def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOADS_DISCORD_BOT_TOKEN", "planted-token")
    monkeypatch.setenv("TOADS_DISCORD_GUILD_ID", "123")
    monkeypatch.setenv("TOADS_HUB_API_URL", "http://api:8000")
    monkeypatch.setenv("TOADS_HUB_SERVICE_TOKEN", "svc")


@pytest.mark.security
def test_token_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    assert "planted-token" not in repr(Settings())


def test_bot_builds_without_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    bot = create_bot(Settings())
    assert bot.intents.members
