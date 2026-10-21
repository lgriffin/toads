"""`/bankrequest <item> <quantity>`: a member asks the guild bank for an item (docs/bank-desk.md).

The request lands on the Bank page's request desk, where officers approve or deny it with a message; the Toad Bot DMs
the member the answer from the hub's outbox (cogs/community.py). The bot only carries the ask: the hub reads the
member's roles from Discord and keeps the request on their record.
"""

from __future__ import annotations

import logging
from typing import Any

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from toads_bot.hub import HubClient

log = logging.getLogger(__name__)

# The hub's limits (toads_api.bank_desk.service), so Discord refuses a bad ask before it is sent.
ITEM_LIMIT = 100
MAX_QUANTITY = 1000
NO_PINGS = discord.AllowedMentions.none()
REFUSALS = {
    401: (
        "The hub did not accept the Toad Bot's call. Tell a super admin: the bot and the API may hold different "
        "TOADS_HUB_SERVICE_TOKEN values, or the API is older than the bot."
    ),
    403: "Only members of the Toads Discord can ask the guild bank for items.",
    503: "Discord is not answering the hub right now. Try again in a minute.",
}


def refusal(response: httpx.Response) -> str:
    if response.status_code in REFUSALS:
        return REFUSALS[response.status_code]
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return f"The bank could not take that request: {detail}"
    return f"The hub refused the request ({response.status_code})."


def receipt(request: dict[str, Any]) -> str:
    return (
        f"Request #{request['id']} for {request['item']} x{request['quantity']} is with the officers. "
        "You will get a DM from the Toad Bot when they answer, and you can follow it on the Bank page."
    )


class BankDesk(commands.Cog):
    def __init__(self, hub: HubClient) -> None:
        self.hub = hub

    @app_commands.command(name="bankrequest", description="Ask the guild bank for an item")
    @app_commands.describe(item="The item you need, as it is named in game", quantity="How many")
    async def bank_request(
        self,
        interaction: discord.Interaction[Any],
        item: app_commands.Range[str, 1, ITEM_LIMIT],
        quantity: app_commands.Range[int, 1, MAX_QUANTITY],
    ) -> None:
        await self.ask(interaction, item, quantity)

    async def ask(self, interaction: Any, item: str, quantity: int) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = await self.hub.bank_request(interaction.user.id, item, quantity)
        except httpx.HTTPError as e:
            log.error("cannot reach the hub at %s for a bank request: %s", self.hub.base_url, e)
            await interaction.followup.send("The hub is not answering. Try again in a minute.", ephemeral=True)
            return
        text = receipt(response.json()) if response.status_code == 201 else refusal(response)
        await interaction.followup.send(text, ephemeral=True, allowed_mentions=NO_PINGS)
