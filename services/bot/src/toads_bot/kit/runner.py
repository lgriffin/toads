"""Each run: registers the bot again (so an API restart never leaves it unknown), resends events the hub could not
take, then pulls the bot's site actions, hands each to its binding and reports the result. Discord-free, so the whole
path can be tested with a fake link."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import httpx

from toads_bot.kit.binding import ActionHandler
from toads_bot.kit.contract import ActionResult, BotManifest, SiteAction
from toads_bot.kit.delivery import EventOutbox
from toads_bot.kit.link import HubLink

log = logging.getLogger(__name__)


class ActionRunner:
    def __init__(
        self,
        manifest: BotManifest,
        link: HubLink,
        handlers: Mapping[str, ActionHandler],
        outbox: EventOutbox | None = None,
    ) -> None:
        self.manifest = manifest
        self.bot = manifest.name
        self.link = link
        self.handlers = dict(handlers)
        self.outbox = outbox or EventOutbox()
        # Results the hub has not heard yet. An action that comes back is answered from here, never run twice.
        self._unreported: dict[int, ActionResult] = {}

    async def run_once(self) -> int:
        """Carry out every pending action once; returns how many were handled. A hub outage waits for the next run."""
        try:
            await self.link.register(self.manifest)
            await self.outbox.flush(self.link, self.manifest)
            actions = await self.link.pull(self.bot)
        except httpx.HTTPError:
            log.warning("hub unreachable for %s; trying again next run", self.bot, exc_info=True)
            return 0
        for action in actions:
            result = self._unreported.get(action.id) or await self._run(action)
            try:
                await self.link.report(self.bot, action.id, result)
            except httpx.HTTPError:
                # The action stays pending on the hub and comes back next run; its result is answered from memory.
                self._unreported[action.id] = result
                log.warning("could not report action %s for %s", action.id, self.bot, exc_info=True)
            else:
                self._unreported.pop(action.id, None)
        return len(actions)

    async def _run(self, action: SiteAction) -> ActionResult:
        handler = self.handlers.get(action.kind)
        if handler is None:
            return ActionResult(ok=False, error=f"no handler for {action.kind}")
        try:
            refs = await handler(action)
        except Exception as exc:
            # One bad action must not stop the rest; the hub retries it and gives up after a few attempts.
            log.warning("action %s (%s) failed", action.id, action.kind, exc_info=True)
            return ActionResult(ok=False, error=f"{type(exc).__name__}: {exc}"[:500])
        return ActionResult(refs=refs or {})
