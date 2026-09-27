"""Guild story, mirrored Discord channels and the interview-room category: configuration, not code."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class MirroredChannel(BaseModel):
    """A Discord channel whose messages the bot offers to the hub for curation."""

    channel_id: int = Field(gt=0)
    # None: guild-wide (global officers curate); otherwise that raid day's officers curate.
    raid_day: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")


class CommunityConfig(BaseModel):
    guild: str = "Toads"
    realm: str = "Spineshatter EU"
    tagline: str = ""
    story: list[str] = []
    discord_invite: str | None = None
    mirrored_channels: list[MirroredChannel] = []
    # Where hub posts go when an officer ticks "also post to Discord". Keyed by raid day; "guild" for guild-wide.
    post_channels: dict[str, int] = {}
    interview_category_id: int | None = None

    @field_validator("discord_invite")
    @classmethod
    def _invite_is_discord(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("https://discord.gg/", "https://discord.com/invite/")):
            raise ValueError("discord_invite must be a https://discord.gg/ or https://discord.com/invite/ link")
        return v

    @classmethod
    def load(cls, path: Path) -> CommunityConfig:
        if not path.exists():
            return cls()
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def mirrored(self, channel_id: int) -> MirroredChannel | None:
        return next((c for c in self.mirrored_channels if c.channel_id == channel_id), None)
