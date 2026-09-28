"""The site's side of the two-way bot bridge: which bots exist, what the site has asked them to do, and who on the site
listens for their Discord events. Rules only; routes live in toads_api.bots.routes and storage behind BridgeStore.

Site to Discord: a feature calls `send(bot, kind, payload)`; the bot pulls pending actions, carries them out and
reports an ActionResult, which reaches any `on_result` listener (to keep the message id a post became, say).
Discord to site: the bot posts a DiscordEvent; `receive` drops resends by `event_id` and hands it to every
`on_event` listener for that bot and kind.

Who may trigger what is not decided here yet: the routes accept only the bot's service token, and listeners get the
Discord user id unverified. Member-level permissions belong in the listener or a later gate.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from toads_api.bots.models import ActionResult, BotManifest, DiscordEvent, EventReceipt, SiteAction

EventListener = Callable[[str, DiscordEvent], None]
ResultListener = Callable[[SiteAction, ActionResult], None]

MAX_PULL = 50
MAX_ATTEMPTS = 5


class BridgeError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status


class BridgeStore(Protocol):
    """Where bots, pending actions and seen event ids live. In memory for now; a table replaces it without touching
    the rules."""

    def save_manifest(self, manifest: BotManifest) -> None: ...
    def manifests(self) -> list[BotManifest]: ...
    def add_action(self, bot: str, kind: str, payload: dict[str, object], at: datetime) -> SiteAction: ...
    def pending(self, bot: str, limit: int) -> list[SiteAction]: ...
    def get_action(self, action_id: int) -> SiteAction | None: ...
    def finish(self, action_id: int, result: ActionResult) -> None: ...
    def retry(self, action_id: int) -> None: ...
    def seen(self, bot: str, event_id: str) -> bool:
        """True if this event was seen before; records it otherwise."""
        ...


@dataclass
class InMemoryBridgeStore:
    _manifests: dict[str, BotManifest] = field(default_factory=dict)
    _actions: dict[int, SiteAction] = field(default_factory=dict)
    _done: dict[int, ActionResult] = field(default_factory=dict)
    _events: set[tuple[str, str]] = field(default_factory=set)
    _next: int = 1

    def save_manifest(self, manifest: BotManifest) -> None:
        self._manifests[manifest.name] = manifest

    def manifests(self) -> list[BotManifest]:
        return sorted(self._manifests.values(), key=lambda m: m.name)

    def add_action(self, bot: str, kind: str, payload: dict[str, object], at: datetime) -> SiteAction:
        action = SiteAction(id=self._next, bot=bot, kind=kind, payload=dict(payload), created_at=at)
        self._actions[action.id] = action
        self._next += 1
        return action

    def pending(self, bot: str, limit: int) -> list[SiteAction]:
        waiting = [a for a in self._actions.values() if a.bot == bot and a.id not in self._done]
        return sorted(waiting, key=lambda a: a.id)[:limit]

    def get_action(self, action_id: int) -> SiteAction | None:
        return self._actions.get(action_id)

    def finish(self, action_id: int, result: ActionResult) -> None:
        self._done[action_id] = result

    def retry(self, action_id: int) -> None:
        action = self._actions[action_id]
        self._actions[action_id] = action.model_copy(update={"attempts": action.attempts + 1})

    def seen(self, bot: str, event_id: str) -> bool:
        key = (bot, event_id)
        if key in self._events:
            return True
        self._events.add(key)
        return False


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

    def complete(self, bot: str, action_id: int, result: ActionResult) -> SiteAction:
        """Record the bot's answer. A failed action is offered again until MAX_ATTEMPTS, then given up."""
        action = self._store.get_action(action_id)
        if action is None or action.bot != bot:
            raise BridgeError(404, "no such action for this bot")
        if not result.ok and action.attempts + 1 < MAX_ATTEMPTS:
            self._store.retry(action_id)
            return action
        self._store.finish(action_id, result)
        for listener in self._result_listeners.get((bot, action.kind), []):
            listener(action, result)
        return action

    def on_result(self, bot: str, kind: str) -> Callable[[ResultListener], ResultListener]:
        def register(listener: ResultListener) -> ResultListener:
            self._result_listeners.setdefault((bot, kind), []).append(listener)
            return listener

        return register

    # ---------------------------------------------------------- Discord to site

    def receive(self, bot: str, event: DiscordEvent) -> EventReceipt:
        manifest = self.manifest(bot)
        if manifest is None:
            raise BridgeError(409, f"bot {bot!r} has not registered")
        if event.kind not in manifest.events:
            raise BridgeError(422, f"bot {bot!r} did not declare {event.kind!r} events")
        if self._store.seen(bot, event.event_id):
            return EventReceipt(accepted=True, duplicate=True)
        handled: list[str] = []
        for name, listener in self._event_listeners.get((bot, event.kind), []):
            listener(bot, event)
            handled.append(name)
        return EventReceipt(accepted=True, handled_by=handled)

    def on_event(self, bot: str, kind: str, *, name: str) -> Callable[[EventListener], EventListener]:
        """Listen for one bot's events of one kind. `name` shows in the receipt, so the bot can log who took it."""

        def register(listener: EventListener) -> EventListener:
            self._event_listeners.setdefault((bot, kind), []).append((name, listener))
            return listener

        return register
