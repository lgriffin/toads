"""The site's side of the two-way bot bridge: which bots exist, what the site has asked them to do, and who on the site
listens for their Discord events. Rules only; routes live in toads_api.bots.routes and storage behind BridgeStore.

Site to Discord: a feature calls `send(bot, kind, payload)`; the bot pulls pending actions, carries them out and
reports an ActionResult, which reaches any `on_result` listener (to keep the message id a post became, say).
Discord to site: the bot posts a DiscordEvent; `receive` hands it to each `on_event` listener for that bot and kind
that has not already handled that `event_id`, so a resend reaches only the listeners that missed it.

Who may trigger what is not decided here yet: the routes accept only the bot's service token, and listeners get the
Discord user id unverified. Member-level permissions belong in the listener or a later gate.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from toads_api.bots.models import ActionResult, BotManifest, DiscordEvent, EventReceipt, SiteAction

log = logging.getLogger(__name__)

EventListener = Callable[[str, DiscordEvent], None]
ResultListener = Callable[[SiteAction, ActionResult], None]

MAX_PULL = 50
MAX_ATTEMPTS = 5
# How many finished actions and handled events the in-memory store remembers, so answers and events that arrive
# twice stay harmless without the store growing forever.
MEMORY = 10_000


class BridgeError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


class BridgeStore(Protocol):
    """Where bots, pending actions and handled events live. In memory for now; a table replaces it without touching
    the rules."""

    def save_manifest(self, manifest: BotManifest) -> None: ...
    def manifests(self) -> list[BotManifest]: ...
    def add_action(self, bot: str, kind: str, payload: dict[str, object], at: datetime) -> SiteAction: ...
    def pending(self, bot: str, limit: int) -> list[SiteAction]: ...
    def get_action(self, action_id: int) -> SiteAction | None:
        """A pending action, or None once it is finished or unknown."""
        ...

    def is_finished(self, action_id: int) -> bool: ...
    def finish(self, action_id: int) -> None: ...
    def retry(self, action_id: int) -> None: ...
    def was_handled(self, bot: str, event_id: str, listener: str) -> bool: ...
    def mark_handled(self, bot: str, event_id: str, listener: str) -> None: ...


def _remember(memory: OrderedDict[Any, None], key: Any) -> None:
    memory[key] = None
    memory.move_to_end(key)
    while len(memory) > MEMORY:
        memory.popitem(last=False)


@dataclass
class InMemoryBridgeStore:
    _manifests: dict[str, BotManifest] = field(default_factory=dict)
    _pending: dict[int, SiteAction] = field(default_factory=dict)
    _finished: OrderedDict[int, None] = field(default_factory=OrderedDict)
    _handled: OrderedDict[tuple[str, str, str], None] = field(default_factory=OrderedDict)
    _next: int = 1

    def save_manifest(self, manifest: BotManifest) -> None:
        self._manifests[manifest.name] = manifest

    def manifests(self) -> list[BotManifest]:
        return sorted(self._manifests.values(), key=lambda m: m.name)

    def add_action(self, bot: str, kind: str, payload: dict[str, object], at: datetime) -> SiteAction:
        action = SiteAction(id=self._next, bot=bot, kind=kind, payload=dict(payload), created_at=at)
        self._pending[action.id] = action
        self._next += 1
        return action

    def pending(self, bot: str, limit: int) -> list[SiteAction]:
        # Dicts keep insertion order, which is id order.
        return [a for a in self._pending.values() if a.bot == bot][:limit]

    def get_action(self, action_id: int) -> SiteAction | None:
        return self._pending.get(action_id)

    def is_finished(self, action_id: int) -> bool:
        return action_id in self._finished

    def finish(self, action_id: int) -> None:
        self._pending.pop(action_id, None)
        _remember(self._finished, action_id)

    def retry(self, action_id: int) -> None:
        action = self._pending[action_id]
        self._pending[action_id] = action.model_copy(update={"attempts": action.attempts + 1})

    def was_handled(self, bot: str, event_id: str, listener: str) -> bool:
        return (bot, event_id, listener) in self._handled

    def mark_handled(self, bot: str, event_id: str, listener: str) -> None:
        _remember(self._handled, (bot, event_id, listener))


class BotBridge:
    def __init__(self, store: BridgeStore, clock: Callable[[], float]) -> None:
        self._store = store
        self._clock = clock
        self._event_listeners: dict[tuple[str, str], list[tuple[str, EventListener]]] = {}
        self._result_listeners: dict[tuple[str, str], list[ResultListener]] = {}

    def _now(self) -> datetime:
        return datetime.fromtimestamp(self._clock(), UTC)

    # ------------------------------------------------------------------ registry

    def register(self, manifest: BotManifest) -> BotManifest:
        self._store.save_manifest(manifest)
        return manifest

    def bots(self) -> list[BotManifest]:
        return self._store.manifests()

    def manifest(self, bot: str) -> BotManifest | None:
        return next((m for m in self._store.manifests() if m.name == bot), None)

    # ---------------------------------------------------------- site to Discord

    def send(self, bot: str, kind: str, payload: dict[str, object] | None = None) -> SiteAction:
        """Queue an action for a bot. A bot that has registered must have declared the kind; one that has not
        started yet still gets the action when it does."""
        manifest = self.manifest(bot)
        if manifest is not None and kind not in manifest.actions:
            raise BridgeError(422, f"bot {bot!r} does not carry out {kind!r}")
        return self._store.add_action(bot, kind, payload or {}, self._now())

    def pending(self, bot: str, limit: int = MAX_PULL) -> list[SiteAction]:
        return self._store.pending(bot, max(1, min(limit, MAX_PULL)))

    def complete(self, bot: str, action_id: int, result: ActionResult) -> None:
        """Record the bot's answer. A failed action is offered again until MAX_ATTEMPTS, then given up. An answer to
        a finished action (a bot resending after a lost response) changes nothing and reaches no listener."""
        action = self._store.get_action(action_id)
        if action is None:
            if self._store.is_finished(action_id):
                return
            raise BridgeError(404, "no such action")
        if action.bot != bot:
            raise BridgeError(404, "no such action for this bot")
        if not result.ok and action.attempts + 1 < MAX_ATTEMPTS:
            self._store.retry(action_id)
            return
        self._store.finish(action_id)
        for listener in self._result_listeners.get((bot, action.kind), []):
            try:
                listener(action, result)
            except Exception:
                # The bot's answer is recorded either way; a broken listener must not make the bot act twice.
                log.exception("result listener for %s/%s failed", bot, action.kind)

    def on_result(self, bot: str, kind: str) -> Callable[[ResultListener], ResultListener]:
        def register(listener: ResultListener) -> ResultListener:
            self._result_listeners.setdefault((bot, kind), []).append(listener)
            return listener

        return register

    # ---------------------------------------------------------- Discord to site

    def receive(self, bot: str, event: DiscordEvent) -> EventReceipt:
        """Hand the event to each listener that has not handled it yet. A listener that fails is retried when the bot
        resends (it gets 503 and keeps the event); the listeners that already took it are not called again."""
        manifest = self.manifest(bot)
        if manifest is None:
            raise BridgeError(409, f"bot {bot!r} has not registered")
        if event.kind not in manifest.events:
            raise BridgeError(422, f"bot {bot!r} did not declare {event.kind!r} events")
        handled: list[str] = []
        failed: list[str] = []
        listeners = self._event_listeners.get((bot, event.kind), [])
        for name, listener in listeners:
            if self._store.was_handled(bot, event.event_id, name):
                continue
            try:
                listener(bot, event)
            except Exception:
                log.exception("listener %s failed on %s/%s", name, bot, event.event_id)
                failed.append(name)
                continue
            self._store.mark_handled(bot, event.event_id, name)
            handled.append(name)
        if failed:
            raise BridgeError(503, f"listeners failed: {', '.join(failed)}; resend the event")
        duplicate = bool(listeners) and not handled
        return EventReceipt(accepted=True, duplicate=duplicate, handled_by=handled)

    def on_event(self, bot: str, kind: str, *, name: str) -> Callable[[EventListener], EventListener]:
        """Listen for one bot's events of one kind. `name` shows in the receipt, so the bot can log who took it."""

        def register(listener: EventListener) -> EventListener:
            self._event_listeners.setdefault((bot, kind), []).append((name, listener))
            return listener

        return register
