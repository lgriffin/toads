"""The bot bridge's wire contract, the bot's copy (docs/bots.md). toads_api.bots.models holds the site's copy, since
the bot cannot import toads_api; tests/test_bot_contract.py checks the two stay the same."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

NAME = r"^[a-z][a-z0-9_-]{0,39}$"
KIND = r"^[a-z][a-z0-9_.]{0,63}$"


class BotManifest(BaseModel):
    """What a bot says about itself when it starts: the site actions it carries out and the Discord events it sends."""

    name: str = Field(pattern=NAME)
    description: str = Field(default="", max_length=500)
    actions: list[str] = Field(default_factory=list, max_length=100)
    events: list[str] = Field(default_factory=list, max_length=100)


class SiteAction(BaseModel):
    """Site to Discord: something the site asks one bot to do (post a message, open a channel, ...)."""

    id: int
    bot: str = Field(pattern=NAME)
    kind: str = Field(pattern=KIND)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    attempts: int = 0


class ActionResult(BaseModel):
    """The bot's answer to a site action. `refs` carries the Discord ids it made (message_id, channel_id, ...)."""

    ok: bool = True
    refs: dict[str, int | str] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=500)


class DiscordEvent(BaseModel):
    """Discord to site: something that happened in Discord that a bot passes on. `event_id` makes resends harmless."""

    event_id: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern=KIND)
    occurred_at: datetime
    guild_id: int | None = None
    channel_id: int | None = None
    user_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventReceipt(BaseModel):
    accepted: bool
    duplicate: bool = False
    handled_by: list[str] = Field(default_factory=list)
