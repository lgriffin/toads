"""The bank binding: the guild bank (ToadsBank, through the hub) in Discord. See docs/bank.md.

- Site to Discord: `bank.dm` sends a member a DM (a manager's carries Approve / Reject / Record delivery buttons) and
  `bank.post` posts in one of the bot's channels. Nothing it says can ping anyone, and the hub has already escaped
  every name in what it asks the bot to say.
- Slash commands: `/bank import` (a modal to paste the addon's export parts), `/bank find <item>` and
  `/bank request <item> <quantity> <character>`. Every answer is ephemeral.
- Buttons carry what they act on in their custom id (`bank:<action>:<args>`), so they keep working across bot
  restarts. Manager buttons carry the request's revision: a stale one gets the request's current state (TB-BM-16).

The bot calls only the hub, as the member who pressed the button (bank_api); ToadsBank decides the rest. The Discord
side is kept thin: the methods below take any interaction-like object, which the tests fake.
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

import discord
from discord import app_commands
from discord.ext import commands

from toads_bot.kit.bank_api import BankApi, BankApiError, HttpBankApi
from toads_bot.kit.binding import Binding, BotContext, Refs
from toads_bot.kit.contract import SiteAction

log = logging.getLogger(__name__)

NO_PINGS = discord.AllowedMentions.none()
PREFIX = "bank"
MODAL_FIELDS = 5
FIELD_LIMIT = 4000
LIST_LIMIT = 10
MESSAGE_LIMIT = 1900
_MARKDOWN = re.compile(r"([\\*_~`|>#\-\[\]()<@:])")


# ------------------------------------------------------------------ wording


def escape(value: object, limit: int = 64) -> str:
    """A name from the bank, safe in a Discord message: one line, bounded, markdown and mention syntax escaped."""
    text = " ".join(str(value if value is not None else "").split())[:limit]
    return _MARKDOWN.sub(r"\\\1", text)


def clip(text: str) -> str:
    return text if len(text) <= MESSAGE_LIMIT else text[: MESSAGE_LIMIT - 1] + "…"


def combine_fields(values: list[str]) -> str:
    """The modal's paragraph fields as one paste; the hub's reader skips blank lines and code fences."""
    return "\n".join(v for v in values if v and v.strip())


def _numbers(values: Any) -> str:
    return ", ".join(str(int(v)) for v in values) if isinstance(values, list) and values else "none"


def progress_text(result: dict[str, Any]) -> str:
    received, total = result.get("received") or [], int(result.get("total") or 0)
    if result.get("complete"):
        return f"All {total} parts received."
    return f"Received parts {_numbers(received)} of {total}. Still missing: {_numbers(result.get('missing'))}."


def preview_text(preview: dict[str, Any]) -> str:
    source = preview.get("source") or {}
    matched = preview.get("matchedSource")
    bank = (
        f"**{escape(matched.get('name'))}**"
        if isinstance(matched, dict)
        else f"an unregistered bank ({escape(source.get('guild'))}, {escape(source.get('realm'))} "
        f"{escape(source.get('region'), 8)})"
    )
    uploader = preview.get("uploader") or {}
    lines = [
        f"Snapshot of {bank}, captured <t:{int(preview.get('capturedAt') or 0)}:f> by {escape(uploader.get('name'))}.",
    ]
    for tab in (preview.get("tabs") or [])[:LIST_LIMIT]:
        status = "" if tab.get("status") == "observed" else f" ({escape(tab.get('status'), 20)})"
        lines.append(
            f"Tab {int(tab.get('index') or 0)} {escape(tab.get('name'))}{status}: "
            f"{int(tab.get('items') or 0)} items in {int(tab.get('occupied') or 0)} slots"
        )
    lines += [f"Warning: {escape(w, 200)}" for w in (preview.get("warnings") or [])[:LIST_LIMIT]]
    if preview.get("existingReceipt"):
        lines.append("This snapshot was accepted before; accepting again changes nothing.")
    if not preview.get("stable", True):
        lines.append("The bank changed while it was being captured, so some counts may be off.")
    return clip("\n".join(lines))


def receipt_text(receipt: dict[str, Any]) -> str:
    if receipt.get("duplicate"):
        return "That snapshot was already accepted; nothing changed."
    text = f"Snapshot accepted. Tabs updated: {_numbers(receipt.get('tabsUpdated'))}."
    if receipt.get("tabsNotRead"):
        text += f" Not read, kept as they were: {_numbers(receipt.get('tabsNotRead'))}."
    return text


def inventory_text(inventory: dict[str, Any], query: str) -> str:
    items = inventory.get("items") or []
    if not items:
        return f"Nothing in the bank matches {escape(query)}."
    lines = [
        f"{escape(i.get('name'))}: {int(i.get('available') or 0)} available, {int(i.get('observed') or 0)} in the bank"
        for i in items[:LIST_LIMIT]
    ]
    if len(items) > LIST_LIMIT:
        lines.append(f"…and {len(items) - LIST_LIMIT} more. Narrow the search or use the bank page on the hub.")
    return clip("\n".join(lines))


def pick_item(items: list[dict[str, Any]], name: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The item a member meant: an exact name (any case) wins, else the only one whose name contains theirs."""
    wanted = name.strip().casefold()
    exact = [i for i in items if str(i.get("name", "")).casefold() == wanted]
    if exact:
        return exact[0], exact
    partial = [i for i in items if wanted and wanted in str(i.get("name", "")).casefold()]
    return (partial[0] if len(partial) == 1 else None), partial


def best_source(item: dict[str, Any]) -> dict[str, Any] | None:
    """The bank holding the most of an item that is free to reserve."""
    sources = item.get("sources") or []
    return max(sources, key=lambda s: int(s.get("available") or 0), default=None)


def request_text(request: dict[str, Any]) -> str:
    what = f"{int(request.get('quantity') or 0)} x {escape(request.get('itemName'))}"
    return (
        f"Request {escape(request.get('id'))}: {what} for {escape(request.get('character'))} is "
        f"{escape(request.get('status'), 20)}."
    )


def current_text(current: Any) -> str:
    """TB-BM-16: the request as it is now, when a button carried an old revision."""
    if not isinstance(current, dict):
        return "That request has changed since this message was sent."
    return (
        f"That request has changed since this message was sent. Now: {request_text(current)} "
        f"(revision {int(current.get('revision') or 0)}, delivered {int(current.get('delivered') or 0)})"
    )


def error_text(error: BankApiError) -> str:
    if error.code == "stale_revision":
        return current_text(error.current)
    if error.code == "insufficient_stock":
        available = (error.details or {}).get("available") if isinstance(error.details, dict) else None
        return f"Not enough in stock{f': {int(available)} available' if available is not None else ''}."
    if error.code == "source_stale":
        return "That bank has not been captured recently, so nothing can be reserved from it until someone uploads it."
    if error.status == 403:
        return "You can't do that. Bank managers and officers handle imports and the request queue."
    return escape(error.message, 300) or "Something went wrong; try again."


# ------------------------------------------------------------------- custom ids


def custom_id(action: str, *args: object) -> str:
    return ":".join([PREFIX, action, *(str(a) for a in args)])


def parse_custom_id(value: str) -> tuple[str, list[str]] | None:
    parts = value.split(":")
    if len(parts) < 2 or parts[0] != PREFIX:
        return None
    return parts[1], parts[2:]


def _view(*buttons: tuple[str, str, discord.ButtonStyle]) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for label, cid, style in buttons:
        view.add_item(discord.ui.Button(label=label, custom_id=cid, style=style))
    return view


def manage_view(request_id: str, revision: int) -> discord.ui.View:
    return _view(
        ("Approve", custom_id("approve", request_id, revision), discord.ButtonStyle.success),
        ("Reject", custom_id("reject", request_id, revision), discord.ButtonStyle.danger),
        ("Record delivery", custom_id("deliver", request_id, revision), discord.ButtonStyle.secondary),
    )


# ---------------------------------------------------------------------- modals


class ImportModal(discord.ui.Modal):
    """Up to five paragraph fields of 4,000 characters: two 1,800-character export parts fit in each."""

    def __init__(self, binding: Bank) -> None:
        super().__init__(title="Paste a bank export", timeout=600)
        self.binding = binding
        self.boxes: list[discord.ui.TextInput[ImportModal]] = [
            discord.ui.TextInput(
                label=f"Parts, box {n}",
                style=discord.TextStyle.paragraph,
                max_length=FIELD_LIMIT,
                required=n == 1,
                placeholder="TOADSBANK/1 export=… part=1/5 …" if n == 1 else None,
            )
            for n in range(1, MODAL_FIELDS + 1)
        ]
        for text_input in self.boxes:
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction[Any]) -> None:
        await self.binding.import_text(interaction, combine_fields([f.value for f in self.boxes]))


class DeliveryModal(discord.ui.Modal):
    def __init__(self, binding: Bank, request_id: str, revision: int) -> None:
        super().__init__(title="Record a delivery", timeout=600)
        self.binding = binding
        self.request_id = request_id
        self.revision = revision
        self.quantity: discord.ui.TextInput[DeliveryModal] = discord.ui.TextInput(
            label="Quantity handed over", max_length=5, required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction[Any]) -> None:
        await self.binding.deliver(interaction, self.request_id, self.revision, self.quantity.value)


# --------------------------------------------------------------------- binding


class Bank(Binding):
    site_actions: ClassVar[dict[str, str]] = {"bank.dm": "dm", "bank.post": "post"}
    discord_events: ClassVar[tuple[str, ...]] = ()

    group = app_commands.Group(name="bank", description="The Toads guild bank")

    def __init__(self, bot: commands.Bot, ctx: BotContext, api: BankApi | None = None) -> None:
        super().__init__(bot, ctx)
        self.api: BankApi = api or HttpBankApi(ctx.hub_api_url, ctx.hub_service_token)
        # The import session each member is filling, by Discord user id. Lost on restart: the next paste opens anew.
        self.imports: dict[int, str] = {}

    # ---------------------------------------------------------- site actions

    async def dm(self, action: SiteAction) -> Refs:
        user = await self.bot.fetch_user(int(action.payload["user_id"]))
        manage = action.payload.get("manage")
        kwargs: dict[str, Any] = {"allowed_mentions": NO_PINGS}
        if isinstance(manage, dict) and manage.get("request_id"):
            kwargs["view"] = manage_view(str(manage["request_id"]), int(manage.get("revision") or 0))
        sent = await user.send(str(action.payload["content"])[:2000], **kwargs)
        return {"message_id": int(sent.id)}

    async def post(self, action: SiteAction) -> Refs:
        channel_id = int(action.payload["channel_id"])
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel | discord.Thread) or channel_id not in self.ctx.channel_ids:
            raise LookupError(f"channel {channel_id} is not one of this bot's channels")
        sent = await channel.send(str(action.payload["content"])[:2000], allowed_mentions=NO_PINGS)
        return {"channel_id": channel_id, "message_id": int(sent.id)}

    # -------------------------------------------------------- slash commands

    @group.command(name="import", description="Paste a bank export from the ToadsBank addon")
    async def import_command(self, interaction: discord.Interaction[Any]) -> None:
        await self.open_import_modal(interaction)

    @group.command(name="find", description="Search the guild bank")
    @app_commands.describe(item="Part of an item's name")
    async def find_command(self, interaction: discord.Interaction[Any], item: str) -> None:
        await self.find(interaction, item)

    @group.command(name="request", description="Ask the guild bank for an item")
    @app_commands.describe(item="The item's name", quantity="How many", character="Who it is for")
    async def request_command(
        self,
        interaction: discord.Interaction[Any],
        item: str,
        quantity: app_commands.Range[int, 1, 10000],
        character: str,
    ) -> None:
        await self.request(interaction, item, int(quantity), character)

    # ------------------------------------------------------------- the logic

    async def _reply(self, interaction: Any, content: str, view: discord.ui.View | None = None) -> None:
        kwargs: dict[str, Any] = {"ephemeral": True, "allowed_mentions": NO_PINGS}
        if view is not None:
            kwargs["view"] = view
        await interaction.followup.send(clip(content), **kwargs)

    async def _defer(self, interaction: Any) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

    async def _officer_day(self, member: int) -> str | None:
        """Manager routes are scoped to a raid day on the hub: the first day the member is an officer for."""
        days = (await self.api.me(member)).get("officer_days") or []
        return str(days[0]) if days else None

    async def open_import_modal(self, interaction: Any) -> None:
        await interaction.response.send_modal(ImportModal(self))

    async def import_text(self, interaction: Any, text: str) -> None:
        await self._defer(interaction)
        member = int(interaction.user.id)
        try:
            day = await self._officer_day(member)
            if day is None:
                await self._reply(interaction, "Only officers can import bank snapshots.")
                return
            import_id, result = await self._add_parts(member, day, text, str(interaction.id))
            if not result.get("complete"):
                await self._reply(interaction, progress_text(result))
                return
            preview = await self.api.preview(member, day, import_id)
        except BankApiError as error:
            await self._reply(interaction, error_text(error))
            return
        view = _view(
            ("Accept", custom_id("accept", import_id), discord.ButtonStyle.success),
            ("Cancel", custom_id("discard", import_id), discord.ButtonStyle.secondary),
        )
        await self._reply(interaction, f"{progress_text(result)}\n{preview_text(preview)}", view)

    async def _add_parts(self, member: int, day: str, text: str, key: str) -> tuple[str, dict[str, Any]]:
        """Adds the paste to the member's open import, opening one if needed or if theirs has expired."""
        import_id = self.imports.get(member)
        if import_id is not None:
            try:
                return import_id, await self.api.add_parts(member, day, import_id, text, f"parts:{key}")
            except BankApiError as error:
                if error.code not in ("import_expired", "not_found"):
                    raise
        import_id = str((await self.api.open_import(member, day, f"open:{key}"))["id"])
        self.imports[member] = import_id
        return import_id, await self.api.add_parts(member, day, import_id, text, f"parts:{key}")

    async def find(self, interaction: Any, query: str) -> None:
        await self._defer(interaction)
        try:
            inventory = await self.api.inventory(int(interaction.user.id), query)
        except BankApiError as error:
            await self._reply(interaction, error_text(error))
            return
        await self._reply(interaction, inventory_text(inventory, query))

    async def request(self, interaction: Any, item: str, quantity: int, character: str) -> None:
        await self._defer(interaction)
        member = int(interaction.user.id)
        try:
            inventory = await self.api.inventory(member, item)
        except BankApiError as error:
            await self._reply(interaction, error_text(error))
            return
        match, candidates = pick_item(inventory.get("items") or [], item)
        if match is None:
            if candidates:
                names = ", ".join(escape(c.get("name")) for c in candidates[:LIST_LIMIT])
                await self._reply(interaction, f"Several items match: {names}. Use the full name.")
            else:
                await self._reply(interaction, f"Nothing in the bank is called {escape(item)}.")
            return
        source = best_source(match)
        if source is None:
            await self._reply(interaction, f"No bank you can see holds {escape(match.get('name'))}.")
            return
        body = {
            "sourceId": str(source["sourceId"]),
            "itemId": int(match["itemId"]),
            "quantity": quantity,
            "character": character.strip(),
        }
        await self._create(interaction, member, body, f"request:{interaction.id}")

    async def _create(self, interaction: Any, member: int, body: dict[str, Any], key: str) -> None:
        try:
            created = await self.api.create_request(member, body, key)
        except BankApiError as error:
            details = error.details if isinstance(error.details, dict) else {}
            waitlist = custom_id("waitlist", body["sourceId"], body["itemId"], body["quantity"], body["character"])
            if error.code == "insufficient_stock" and details.get("canWaitlist") and len(waitlist) <= 100:
                view = _view(("Join the waitlist", waitlist, discord.ButtonStyle.primary))
                await self._reply(interaction, f"{error_text(error)} Join the waitlist instead?", view)
            else:
                await self._reply(interaction, error_text(error))
            return
        await self._reply(interaction, request_text(created))

    async def deliver(self, interaction: Any, request_id: str, revision: int, quantity: str) -> None:
        if not quantity.strip().isdigit() or int(quantity) < 1:
            await interaction.response.send_message("Give the quantity as a whole number.", ephemeral=True)
            return
        await self._manage(interaction, request_id, revision, "deliveries", {"quantity": int(quantity)})

    async def _manage(
        self, interaction: Any, request_id: str, revision: int, action: str, extra: dict[str, Any] | None = None
    ) -> None:
        await self._defer(interaction)
        member = int(interaction.user.id)
        try:
            day = await self._officer_day(member)
            if day is None:
                await self._reply(interaction, "Only officers can manage bank requests.")
                return
            body = {"expectedRevision": revision, **(extra or {})}
            # Keyed on the request's revision, so a double click is answered once and never applied twice.
            key = f"{action}:{request_id}:{revision}"
            updated = await self.api.manage(member, day, request_id, action, body, key)
        except BankApiError as error:
            await self._reply(interaction, error_text(error))
            return
        await self._reply(interaction, request_text(updated))

    # ----------------------------------------------------------------- buttons

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Any) -> None:
        if interaction.type != discord.InteractionType.component:
            return
        data = interaction.data if isinstance(interaction.data, dict) else {}
        parsed = parse_custom_id(str(data.get("custom_id", "")))
        if parsed is None:
            return
        await self.press(interaction, *parsed)

    async def press(self, interaction: Any, action: str, args: list[str]) -> None:
        member = int(interaction.user.id)
        if action in ("approve", "reject") and len(args) == 2 and args[1].isdigit():
            await self._manage(interaction, args[0], int(args[1]), action)
        elif action == "deliver" and len(args) == 2 and args[1].isdigit():
            await interaction.response.send_modal(DeliveryModal(self, args[0], int(args[1])))
        elif action == "accept" and len(args) == 1:
            await self._accept(interaction, member, args[0])
        elif action == "discard" and len(args) == 1:
            if self.imports.get(member) == args[0]:
                del self.imports[member]
            await interaction.response.send_message("Import cancelled; nothing was saved.", ephemeral=True)
        elif action == "waitlist" and len(args) == 4 and args[1].isdigit() and args[2].isdigit():
            await self._defer(interaction)
            body = {
                "sourceId": args[0],
                "itemId": int(args[1]),
                "quantity": int(args[2]),
                "character": args[3],
                "waitlist": True,
            }
            await self._create(interaction, member, body, f"waitlist:{interaction.id}")
        else:
            log.info("unknown bank button %s", action)

    async def _accept(self, interaction: Any, member: int, import_id: str) -> None:
        await self._defer(interaction)
        try:
            day = await self._officer_day(member)
            if day is None:
                await self._reply(interaction, "Only officers can import bank snapshots.")
                return
            receipt = await self.api.accept(member, day, import_id, f"accept:{import_id}")
        except BankApiError as error:
            await self._reply(interaction, error_text(error))
            return
        if self.imports.get(member) == import_id:
            del self.imports[member]
        await self._reply(interaction, receipt_text(receipt))
