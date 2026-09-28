"""A reusable kit for Discord bots bound both ways to the hub (docs/bots.md).

A bot is a BotSpec: a name and the Bindings it runs. Each Binding is a cog that carries out site actions (site to
Discord) and emits Discord events (Discord to site). build_bot turns a spec into a discord.py bot that registers its
manifest with the hub, pulls its actions and reports the results. The hub is reached only through a HubLink.
"""

from toads_bot.kit.binding import Binding, BotContext
from toads_bot.kit.contract import ActionResult, BotManifest, DiscordEvent, EventReceipt, SiteAction
from toads_bot.kit.delivery import EventOutbox
from toads_bot.kit.gate import Gate, OpenGate
from toads_bot.kit.link import HttpHubLink, HubLink
from toads_bot.kit.runner import ActionRunner
from toads_bot.kit.spec import BotSpec, KitSettings, build_bot

__all__ = [
    "ActionResult",
    "ActionRunner",
    "Binding",
    "BotContext",
    "BotManifest",
    "BotSpec",
    "DiscordEvent",
    "EventOutbox",
    "EventReceipt",
    "Gate",
    "HttpHubLink",
    "HubLink",
    "KitSettings",
    "OpenGate",
    "SiteAction",
    "build_bot",
]
