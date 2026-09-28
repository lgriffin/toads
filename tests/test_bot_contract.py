"""The bot bridge's wire models exist twice, since the bot cannot import toads_api (lint-imports): toads_api.bots.models
on the site, toads_bot.kit.contract in the bot. They must describe exactly the same JSON (docs/bots.md)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from toads_api.bots import models as site
from toads_bot.kit import contract as bot

MODELS = ["BotManifest", "SiteAction", "ActionResult", "DiscordEvent", "EventReceipt"]


@pytest.mark.parametrize("name", MODELS)
def test_both_sides_share_the_same_schema(name: str) -> None:
    site_model: type[BaseModel] = getattr(site, name)
    bot_model: type[BaseModel] = getattr(bot, name)
    assert site_model.model_json_schema() == bot_model.model_json_schema()


def test_the_patterns_match() -> None:
    assert (site.NAME, site.KIND) == (bot.NAME, bot.KIND)
