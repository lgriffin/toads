from pathlib import Path

import pytest
from pydantic import ValidationError
from toads_api.community.config import CommunityConfig

from conftest import make_settings

ROOT = Path(__file__).resolve().parents[3]


def test_example_config_loads() -> None:
    cfg = CommunityConfig.load(ROOT / "config" / "community.example.yaml")
    assert cfg.guild == "Toads"
    assert cfg.mirrored_channels == []


def test_missing_config_means_nothing_is_mirrored(tmp_path: Path) -> None:
    cfg = CommunityConfig.load(tmp_path / "absent.yaml")
    assert cfg.mirrored(111) is None


@pytest.mark.security
@pytest.mark.parametrize("invite", ["https://evil.example/", "http://discord.gg/toads", "javascript:alert(1)"])
def test_invite_must_be_a_discord_link(invite: str) -> None:
    with pytest.raises(ValidationError):
        CommunityConfig(discord_invite=invite)


def test_example_env_names_the_service_token() -> None:
    env = (ROOT / "services" / "api" / ".env.example").read_text(encoding="utf-8")
    assert "TOADS_HUB_SERVICE_TOKEN=" in env
    assert "TOADS_COMMUNITY_CONFIG=" in env


@pytest.mark.security
def test_service_token_is_not_in_repr() -> None:
    token = "planted-service-token"  # noqa: S105
    assert token not in repr(make_settings(hub_service_token=token))
