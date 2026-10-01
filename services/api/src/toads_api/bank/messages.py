"""The words the bank bot says, built from ToadsBank's event payloads. Names in payloads are raw (a character can be
called anything the game allows and a Discord name anything at all), so every name is escaped here, and the bot sends
everything with mentions suppressed (TB-DM-08)."""

from __future__ import annotations

import re
from typing import Any

# Discord markdown, quoting, masked links and mention syntax. Escaping `@` and `<` also keeps "@everyone" and
# "<@123>" from even looking like mentions; the bot's AllowedMentions.none() is what guarantees nobody is pinged.
_MARKDOWN = re.compile(r"([\\*_~`|>#\-\[\]()<@:])")
NAME_LIMIT = 64
MESSAGE_LIMIT = 1900

CHANGES = {
    "approved": "was approved",
    "rejected": "was rejected",
    "cancelled": "was cancelled",
    "delivered": "had a delivery recorded",
    "fulfilled": "is fulfilled",
    "expired": "expired",
}


def escape(value: object, limit: int = NAME_LIMIT) -> str:
    """One name, safe to drop into a Discord message: one line, bounded, markdown and mentions escaped."""
    text = " ".join(str(value if value is not None else "").split())[:limit]
    return _MARKDOWN.sub(r"\\\1", text)


def _clip(text: str) -> str:
    return text if len(text) <= MESSAGE_LIMIT else text[: MESSAGE_LIMIT - 1] + "…"


def _what(request: dict[str, Any]) -> str:
    return f"{int(request.get('quantity') or 0)} x {escape(request.get('itemName'))}"


def assigned(request: dict[str, Any]) -> str:
    """To a manager: a request waiting for them, with the buttons the bot adds."""
    lines = [
        f"New bank request: **{_what(request)}** for {escape(request.get('character'))}, "
        f"asked by {escape(request.get('memberName'))}.",
    ]
    if request.get("note"):
        lines.append(f"Note: {escape(request.get('note'), 200)}")
    lines.append(f"Request {escape(request.get('id'))}, revision {int(request.get('revision') or 0)}.")
    return _clip("\n".join(lines))


def updated(request: dict[str, Any], change: str) -> str:
    """To the requester: what happened to their request."""
    verb = CHANGES.get(change, f"changed ({escape(change, 20)})")
    lines = [f"Your bank request for **{_what(request)}** ({escape(request.get('character'))}) {verb}."]
    if change in ("delivered", "fulfilled"):
        lines.append(
            f"Delivered {int(request.get('delivered') or 0)}, still to come {int(request.get('outstanding') or 0)}."
        )
    if request.get("managerNote"):
        lines.append(f"Manager's note: {escape(request.get('managerNote'), 200)}")
    return _clip("\n".join(lines))


def _tabs(values: Any) -> str:
    return ", ".join(str(int(v)) for v in values) if isinstance(values, list) and values else "none"


def snapshot_accepted(source: dict[str, Any], receipt: dict[str, Any], uploader: dict[str, Any] | None) -> str:
    """To the bank channel: a new snapshot of one bank."""
    who = escape((uploader or {}).get("name")) or "someone"
    lines = [
        f"Bank snapshot accepted for **{escape(source.get('name'))}**, uploaded by {who}.",
        f"Tabs updated: {_tabs(receipt.get('tabsUpdated'))}.",
    ]
    if receipt.get("tabsNotRead"):
        lines.append(f"Not read this time (kept at their previous age): {_tabs(receipt.get('tabsNotRead'))}.")
    if receipt.get("tabsKeptAsHistory"):
        history = _tabs(receipt.get("tabsKeptAsHistory"))
        lines.append(f"Older than what the bank already had, kept as history: {history}.")
    return _clip("\n".join(lines))


def dm_failed(request: dict[str, Any]) -> str:
    """To the fallback channel when a manager could not be reached by DM (TB-BM-12)."""
    return _clip(
        f"A bank manager could not be reached by DM about request {escape(request.get('id'))}: "
        f"**{_what(request)}** for {escape(request.get('character'))}, asked by {escape(request.get('memberName'))}. "
        "It is waiting in the queue on the hub."
    )
