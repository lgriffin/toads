"""`/raidhelper import`: an officer hands the Toad Bot a Raid-Helper export (https://raid-helper.dev) and the hub
pre-fills the specs of everyone it seats (docs/comps.md "Importing from Raid-Helper").

The bot only carries the file. The hub decides who may import: it reads the sender's roles from Discord and accepts
the import only from that night's officers, global officers and super admins.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from toads_bot.hub import HubClient

log = logging.getLogger(__name__)

# Raid-Helper's exports are a few tens of kilobytes; a much bigger file is not one.
MAX_EXPORT_BYTES = 512 * 1024
# What a refusal from the hub means, in words for the officer.
REFUSALS = {
    401: "The Toad Bot could not sign in to the hub. Tell a super admin.",
    403: "Only that night's officers can import its sign-ups.",
    404: "The hub has no such raid night.",
    503: "Discord is not answering the hub right now. Try again in a minute.",
}
OUTCOMES = (
    ("added", "pre-filled"),
    ("updated", "updated from an earlier import"),
    ("unchanged", "already up to date"),
    ("kept", "kept (they set their own on Me)"),
    ("skipped", "skipped"),
)


def read_export(raw: bytes) -> dict[str, Any] | None:
    """The export as JSON, or None when the file is not a JSON object."""
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def import_summary(night: str, result: dict[str, Any]) -> str:
    """What the import did, for the officer who ran it: the counts, then who was skipped and why."""
    counts = [f"{result[key]} {words}" for key, words in OUTCOMES if result.get(key)]
    lines = [f"Raid-Helper import for {night}: " + (", ".join(counts) if counts else "nobody to import") + "."]
    skipped = [r for r in result.get("rows", []) if r.get("outcome") == "skipped"]
    for row in skipped[:15]:
        lines.append(f"- {row.get('name')}: {row.get('reason')}")
    if len(skipped) > 15:
        lines.append(f"- and {len(skipped) - 15} more")
    lines.append("Members see what was imported on Me, and can change it there.")
    return "\n".join(lines)[:2000]


def refusal(response: httpx.Response) -> str:
    if response.status_code in REFUSALS:
        return REFUSALS[response.status_code]
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return f"The hub could not read that export: {detail}"
    return f"The hub refused the import ({response.status_code})."


class RaidHelper(commands.Cog):
    group = app_commands.Group(name="raidhelper", description="Raid-Helper sign-ups on the Toads Hub")

    def __init__(self, hub: HubClient) -> None:
        self.hub = hub

    async def night_choices(
        self, interaction: discord.Interaction[Any], current: str
    ) -> list[app_commands.Choice[str]]:
        try:
            nights = await self.hub.raid_nights()
        except httpx.HTTPError:
            return []
        wanted = current.strip().lower()
        return [
            app_commands.Choice(name=n["name"], value=n["id"])
            for n in nights
            if wanted in n["name"].lower() or wanted in n["id"]
        ][:25]

    @group.command(name="import", description="Pre-fill members' specs from a Raid-Helper export")
    @app_commands.describe(night="The raid night the sign-ups are for", export="The file Raid-Helper exported")
    @app_commands.autocomplete(night=night_choices)
    async def import_command(
        self, interaction: discord.Interaction[Any], night: str, export: discord.Attachment
    ) -> None:
        await self.run_import(interaction, night, export)

    async def run_import(self, interaction: Any, night: str, export: Any) -> None:
        if export.size > MAX_EXPORT_BYTES:
            await interaction.response.send_message("That file is too big to be a Raid-Helper export.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        data = read_export(await export.read())
        if data is None:
            await interaction.followup.send("That file is not a Raid-Helper export (it is not JSON).", ephemeral=True)
            return
        try:
            response = await self.hub.import_raid_helper(night, interaction.user.id, data)
        except httpx.HTTPError as e:
            log.error("cannot reach the hub at %s for a Raid-Helper import: %s", self.hub.base_url, e)
            await interaction.followup.send("The hub is not answering. Try again in a minute.", ephemeral=True)
            return
        if response.status_code != 200:
            await interaction.followup.send(refusal(response), ephemeral=True)
            return
        await interaction.followup.send(import_summary(night, response.json()), ephemeral=True)
