"""`/highlight`, `/stream` and `/clip`: members fill the hub's Highlights page from Discord (docs/highlights.md).

- `/highlight <photo> [caption]` posts a photo: 48 hours in the carousel, then the archive for good.
- `/stream start <link> [title]` puts the member's Twitch channel on the page while they are live, and says so in the
  channel; `/stream end` takes it off.
- `/clip <link> <title>` shares a YouTube, Twitch or Streamable clip for a global officer to publish.

The bot only carries what was sent. The hub reads the member's roles from Discord and decides: raiders post, and the
hub re-encodes every photo itself.
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

# The hub's limits (toads_api.gallery), so Discord refuses a bad post before it is sent.
MAX_PHOTO_BYTES = 10 * 1024 * 1024
CAPTION_LIMIT = 200
TITLE_LIMIT = 120
PHOTO_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
NO_PINGS = discord.AllowedMentions.none()
REFUSALS = {
    401: (
        "The hub did not accept the Toad Bot's call. Tell a super admin: the bot and the API may hold different "
        "TOADS_HUB_SERVICE_TOKEN values, or the API is older than the bot."
    ),
    403: "Only the guild's raiders can post to the Highlights page.",
    503: "Discord is not answering the hub right now. Try again in a minute.",
}
UNREACHABLE = "The hub is not answering. Try again in a minute."


def refusal(response: httpx.Response) -> str:
    if response.status_code in REFUSALS:
        return REFUSALS[response.status_code]
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return f"The hub could not take that: {detail}"
    return f"The hub refused it ({response.status_code})."


class Highlights(commands.Cog):
    stream = app_commands.Group(name="stream", description="Show your Twitch stream on the Toads Hub")

    def __init__(self, hub: HubClient, public_url: str = "") -> None:
        self.hub = hub
        self.page = f"{public_url.rstrip('/')}/highlights" if public_url else ""

    def where(self) -> str:
        return f"the Highlights page ({self.page})" if self.page else "the hub's Highlights page"

    # ------------------------------------------------------------ commands

    @app_commands.command(name="highlight", description="Post a photo to the Toads Hub's Highlights page")
    @app_commands.describe(photo="The photo (JPEG, PNG, WebP or GIF, up to 10 MB)", caption="A line about it")
    async def highlight(
        self,
        interaction: discord.Interaction[Any],
        photo: discord.Attachment,
        caption: app_commands.Range[str, 0, CAPTION_LIMIT] = "",
    ) -> None:
        await self.post_photo(interaction, photo, caption)

    @stream.command(name="start", description="Show your live Twitch stream on the Highlights page")
    @app_commands.describe(link="Your Twitch channel, like https://twitch.tv/yourname", title="What you are streaming")
    async def stream_start(
        self,
        interaction: discord.Interaction[Any],
        link: app_commands.Range[str, 1, 200],
        title: app_commands.Range[str, 0, TITLE_LIMIT] = "",
    ) -> None:
        await self.start_stream(interaction, link, title)

    @stream.command(name="end", description="Take your stream off the Highlights page")
    async def stream_end(self, interaction: discord.Interaction[Any]) -> None:
        await self.end_stream(interaction)

    @app_commands.command(name="clip", description="Share a raid clip for the Highlights page's clips")
    @app_commands.describe(link="A YouTube, Twitch clip or Streamable link", title="What happens in it")
    async def clip(
        self,
        interaction: discord.Interaction[Any],
        link: app_commands.Range[str, 1, 300],
        title: app_commands.Range[str, 1, TITLE_LIMIT],
    ) -> None:
        await self.share_clip(interaction, link, title)

    # ---------------------------------------------------------- the work

    async def post_photo(self, interaction: Any, photo: Any, caption: str) -> None:
        kind = (photo.content_type or "").split(";")[0].strip().lower()
        if kind not in PHOTO_TYPES:
            await interaction.response.send_message("Send a photo: JPEG, PNG, WebP or GIF.", ephemeral=True)
            return
        if photo.size > MAX_PHOTO_BYTES:
            await interaction.response.send_message("That photo is over 10 MB.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = await self.hub.post_photo(interaction.user.id, await photo.read(), caption)
        except (httpx.HTTPError, discord.HTTPException) as e:
            log.error("cannot post a photo to the hub at %s: %s", self.hub.base_url, e)
            await interaction.followup.send(UNREACHABLE, ephemeral=True)
            return
        if response.status_code != 201:
            await interaction.followup.send(refusal(response), ephemeral=True, allowed_mentions=NO_PINGS)
            return
        await interaction.followup.send(
            f"Your photo is on {self.where()}: in the carousel for 48 hours, then in the archive for good.",
            ephemeral=True,
        )

    async def start_stream(self, interaction: Any, link: str, title: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            response = await self.hub.start_stream(interaction.user.id, link, title)
        except httpx.HTTPError as e:
            log.error("cannot start a stream on the hub at %s: %s", self.hub.base_url, e)
            await interaction.followup.send(UNREACHABLE, ephemeral=True)
            return
        if response.status_code != 201:
            await interaction.followup.send(refusal(response), ephemeral=True, allowed_mentions=NO_PINGS)
            return
        stream = response.json()
        about = f": {stream['title']}" if stream.get("title") else ""
        await interaction.followup.send(
            f"{stream['streamer_name']} is live on Twitch{about}\nhttps://www.twitch.tv/{stream['channel']}\n"
            f"Watch on {self.where()}.",
            allowed_mentions=NO_PINGS,
        )

    async def end_stream(self, interaction: Any) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = await self.hub.end_stream(interaction.user.id)
        except httpx.HTTPError as e:
            log.error("cannot end a stream on the hub at %s: %s", self.hub.base_url, e)
            await interaction.followup.send(UNREACHABLE, ephemeral=True)
            return
        if response.status_code != 200:
            await interaction.followup.send(refusal(response), ephemeral=True, allowed_mentions=NO_PINGS)
            return
        ended = response.json().get("ended", 0)
        text = "Your stream is off the Highlights page." if ended else "You had no stream on the Highlights page."
        await interaction.followup.send(text, ephemeral=True)

    async def share_clip(self, interaction: Any, link: str, title: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = await self.hub.share_clip(interaction.user.id, link, title)
        except httpx.HTTPError as e:
            log.error("cannot share a clip with the hub at %s: %s", self.hub.base_url, e)
            await interaction.followup.send(UNREACHABLE, ephemeral=True)
            return
        if response.status_code != 201:
            await interaction.followup.send(refusal(response), ephemeral=True, allowed_mentions=NO_PINGS)
            return
        await interaction.followup.send(
            f"Thanks! Your clip is with the officers; once they publish it, it shows in the clips on {self.where()}.",
            ephemeral=True,
        )
