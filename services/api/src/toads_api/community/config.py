"""Mirrored Discord channels, post channels and the interview-room category: configuration, not code.

The Story page's tagline and story are not configuration: they live in the repository (`story.py`). A `tagline` or
`story` left in an older community.yaml is ignored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, StringConstraints, field_validator


class MirroredChannel(BaseModel):
    """A Discord channel whose messages the bot offers to the hub for curation."""

    channel_id: int = Field(gt=0)
    # None: guild-wide (global officers curate); otherwise that raid day's officers curate.
    raid_day: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")


class CommunityConfig(BaseModel):
    guild: str = "Toads"
    realm: str = "Spineshatter EU"
    discord_invite: str | None = None
    mirrored_channels: list[MirroredChannel] = []
    # Where hub posts go when an officer ticks "also post to Discord". Keyed by raid day; "guild" for guild-wide.
    post_channels: dict[str, int] = {}
    interview_category_id: int | None = None
    # Discord user ids (or usernames) of the officers who interview every applicant. When set, the bot opens the
    # interview room the moment someone applies, with just the applicant and these people in it. Ids are safer: a
    # username someone gives up can be taken by another member.
    interviewers: list[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_.]{2,32}$")]] = []

    @field_validator("interviewers", mode="before")
    @classmethod
    def _ids_as_text(cls, v: object) -> object:
        """YAML reads an unquoted user id as a number; keep it as the text the bot matches on."""
        return [str(x) if isinstance(x, int) else x for x in v] if isinstance(v, list) else v

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
