"""Every bot this repo can run, by name. A new bot is a new entry here (and usually a new Binding); run it with
`TOADS_BOT_SPEC=<name> toads-botkit`, one process per bot, each with its own Discord application token."""

from __future__ import annotations

from toads_bot.kit.bank import Bank
from toads_bot.kit.relay import Relay
from toads_bot.kit.spec import BotSpec

RELAY = BotSpec(
    name="relay",
    description="Relays text both ways between the hub and chosen Discord channels.",
    bindings=(Relay,),
    message_content=True,
)

BANK = BotSpec(
    name="bank",
    description="The guild bank (ToadsBank): imports, search, requests and manager DMs. See docs/bank.md.",
    bindings=(Bank,),
)

SPECS: dict[str, BotSpec] = {spec.name: spec for spec in (RELAY, BANK)}
