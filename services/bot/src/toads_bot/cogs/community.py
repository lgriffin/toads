"""Discord side of the community layer: interview rooms, two-way officer posts.

Inbound: messages in the mirrored channels go to the hub, where they wait for an officer. Edits and deletions follow.
Outbound: the bot works through the hub's outbox (open or lock an interview room, post or edit an officer post).
Nothing the bot posts can ping anyone: every send uses AllowedMentions.none().
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

import discord
from discord.ext import commands, tasks

from toads_bot.hub import HubClient

log = logging.getLogger(__name__)

NO_PINGS = discord.AllowedMentions.none()
EMBED_COLOUR = discord.Colour(0x5FBF6A)
HUB_KINDS = frozenset({"create_interview_room", "lock_interview_room", "post_message", "edit_message"})


def interview_channel_name(character: str) -> str:
    """`interview-<character>` in Discord's channel alphabet: lower case ASCII, digits and dashes."""
    ascii_name = unicodedata.normalize("NFKD", character).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:40]
    return f"interview-{slug or 'applicant'}"


def interview_overwrites(
    guild: discord.Guild,
    applicant: discord.abc.Snowflake,
    officer_roles: Sequence[discord.abc.Snowflake],
    me: Any,
    interviewers: Sequence[discord.abc.Snowflake] = (),
) -> dict[Any, discord.PermissionOverwrite]:
    """Private to the applicant, the officers or named interviewers who decide, and the bot. Nobody else can even see
    it exists."""
    talk = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        applicant: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True, mention_everyone=False
        ),
        **{role: talk for role in officer_roles},
        **{person: talk for person in interviewers},
        me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }


async def find_interviewer(guild: discord.Guild, name: str) -> discord.Member | None:
    """An interviewer named in config/community.yaml: a user id, or a Discord username (not a nickname, which anyone
    can change to look like an officer). The member cache comes first; Discord is asked when it misses."""
    if name.isdigit():
        if (cached := guild.get_member(int(name))) is not None:
            return cached
        try:
            return await guild.fetch_member(int(name))
        except discord.NotFound:
            return None
    if (found := next((m for m in guild.members if m.name == name), None)) is not None:
        return found
    # 100 is Discord's most per search, so many members sharing the name's prefix still leave the exact one in.
    return next((m for m in await guild.query_members(query=name, limit=100) if m.name == name), None)


def application_embed(payload: dict[str, Any]) -> discord.Embed:
    """The applicant's answers, in the room's first message so the interviewers start from them."""
    roles = str(payload.get("role") or "?")
    if payload.get("secondary_role"):
        roles += f", then {payload['secondary_role']}"
    embed = discord.Embed(title=f"Application: {payload['character_name']}"[:256], colour=EMBED_COLOUR)
    embed.add_field(name="Class", value=str(payload.get("class_name") or "?")[:1024], inline=True)
    embed.add_field(name="Roles", value=roles[:1024], inline=True)
    embed.add_field(name="Why Toads?", value=str(payload.get("why_toads") or "Not answered")[:1024], inline=False)
    embed.set_footer(text=f"Toads Hub application {payload['application_id']}")
    return embed


def post_embed(post: dict[str, Any]) -> discord.Embed:
    """An officer post as an embed. Text only; the hub stores no HTML and Discord renders none."""
    embed = discord.Embed(title=str(post["title"])[:256], description=str(post["body"])[:4096], colour=EMBED_COLOUR)
    embed.set_footer(text=f"{post['author_name']} · Toads Hub"[:2048])
    return embed


WELCOME = (
    "Welcome, and thanks for applying to Toads! This room is private: only you and the officers who look after "
    "recruitment can see it. Ask us anything; we'll be in touch here about next steps."
)


class Community(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        hub: HubClient,
        *,
        guild_id: int,
        mirror_channel_ids: set[int],
        post_to_channels: bool,
    ) -> None:
        self.bot = bot
        self.hub = hub
        self.guild_id = guild_id
        self.mirror_channel_ids = mirror_channel_ids
        self.post_to_channels = post_to_channels

    async def cog_load(self) -> None:
        self.poll.start()

    async def cog_unload(self) -> None:
        self.poll.cancel()

    # ----------------------------------------------------------------- inbound

    def _mirrored(self, channel_id: int, guild_id: int | None) -> bool:
        return guild_id == self.guild_id and channel_id in self.mirror_channel_ids

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Skip bots, the bot's own outbound posts included, so a post never loops back as a new curation item.
        if message.author.bot or not self._mirrored(message.channel.id, message.guild.id if message.guild else None):
            return
        await self.hub.discord_message(
            channel_id=message.channel.id,
            message_id=message.id,
            author_name=message.author.display_name,
            content=message.content,
            created_at=message.created_at,
        )

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        if not self._mirrored(payload.channel_id, payload.guild_id):
            return
        message = payload.message
        if message.author.bot:
            return
        await self.hub.discord_message(
            channel_id=payload.channel_id,
            message_id=payload.message_id,
            author_name=message.author.display_name,
            content=message.content,
            created_at=message.created_at,
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if self._mirrored(payload.channel_id, payload.guild_id):
            await self.hub.discord_message_deleted(payload.message_id)

    # ---------------------------------------------------------------- outbound

    @tasks.loop(seconds=30)
    async def poll(self) -> None:
        guild = self.bot.get_guild(self.guild_id)
        if guild is not None:
            await self.run_outbox(guild)

    @poll.before_loop
    async def _ready(self) -> None:
        await self.bot.wait_until_ready()

    async def run_outbox(self, guild: discord.Guild) -> None:
        for item in await self.hub.outbox():
            job, post = item["job"], item.get("post")
            try:
                await self._run(guild, job, post)
            except discord.HTTPException:
                # Left un-acked, so the next poll retries it.
                log.warning("outbox job %s (%s) failed", job["id"], job["kind"], exc_info=True)

    async def _run(self, guild: discord.Guild, job: dict[str, Any], post: dict[str, Any] | None) -> None:
        kind, payload, job_id = job["kind"], job["payload"], int(job["id"])
        if kind == "create_interview_room":
            await self.hub.ack(job_id, channel_id=await self.open_interview_room(guild, payload))
        elif kind == "lock_interview_room":
            await self.lock_interview_room(guild, payload)
            await self.hub.ack(job_id)
        elif kind in {"post_message", "edit_message"} and post is not None:
            if not self.post_to_channels:
                return  # posting is behind a feature flag; the job waits until it is switched on
            channel = guild.get_channel(int(payload["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                log.warning("post channel %s is missing", payload["channel_id"])
                return
            if kind == "post_message":
                sent = await channel.send(embed=post_embed(post), allowed_mentions=NO_PINGS)
                await self.hub.ack(job_id, message_id=sent.id)
            else:
                message = await channel.fetch_message(int(payload["message_id"]))
                await message.edit(embed=post_embed(post), allowed_mentions=NO_PINGS)
                await self.hub.ack(job_id)
        else:
            log.warning("unknown outbox job kind %r", kind)

    async def open_interview_room(self, guild: discord.Guild, payload: dict[str, Any]) -> int:
        applicant = guild.get_member(int(payload["discord_user_id"])) or await guild.fetch_member(
            int(payload["discord_user_id"])
        )
        roles = [r for rid in payload.get("officer_role_ids") or [] if (r := guild.get_role(int(rid))) is not None]
        names = [str(n) for n in payload.get("interviewers") or []]
        found = {n: await find_interviewer(guild, n) for n in names}
        interviewers = [m for m in found.values() if m is not None]
        missing = [n for n, m in found.items() if m is None]
        if missing:
            log.warning("interviewers not in the server: %s", ", ".join(missing))
        category = guild.get_channel(int(payload["category_id"])) if payload.get("category_id") else None
        channel = await guild.create_text_channel(
            interview_channel_name(str(payload["character_name"])),
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=interview_overwrites(guild, applicant, roles, guild.me, interviewers),
            reason=f"Toads Hub application {payload['application_id']}",
        )
        greeting = " ".join([applicant.mention, *(m.mention for m in interviewers)])
        note = f"\n\n(Could not find {', '.join(missing)} in the server to add them.)" if missing else ""
        await channel.send(
            f"{greeting} {WELCOME}{note}",
            embed=application_embed(payload),
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=[applicant, *interviewers]),
        )
        return int(channel.id)

    async def lock_interview_room(self, guild: discord.Guild, payload: dict[str, Any]) -> None:
        """Closed applications keep their room for the officers' record; the applicant can read but not post."""
        channel = guild.get_channel(int(payload["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            return
        uid = int(payload["discord_user_id"])
        overwrites = dict(channel.overwrites)
        # Match by id so this works whether or not the applicant is still in the server.
        for target in [t for t in overwrites if t.id == uid]:
            overwrites[target] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        await channel.edit(overwrites=overwrites, reason="Toads Hub application closed")
