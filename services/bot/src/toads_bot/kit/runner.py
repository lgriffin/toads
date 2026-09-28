"""Pulls a bot's site actions from the hub, hands each to its binding and reports the result. Discord-free, so the
whole site-to-Discord path can be tested with a fake link."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import httpx

from toads_bot.kit.binding import ActionHandler
from toads_bot.kit.contract import ActionResult, SiteAction
from toads_bot.kit.link import HubLink

log = logging.getLogger(__name__)


class ActionRunner:
    def __init__(self, bot: str, link: HubLink, handlers: Mapping[str, ActionHandler]) -> None:
        self.bot = bot
        self.link = link
        self.handlers = dict(handlers)

    async def run_once(self) -> int:
        """Carry out every pending action once; returns how many were handled. A hub outage waits for the next run."""
        try:
            actions = await self.link.pull(self.bot)
        except httpx.HTTPError:
            log.warning("could not pull actions for %s", self.bot, exc_info=True)
            return 0
        for action in actions:
            result = await self._run(action)
            try:
                await self.link.report(self.bot, action.id, result)
            except httpx.HTTPError:
                # Unreported actions stay pending on the hub, so they come back on the next run.
                log.warning("could not report action %s for %s", action.id, self.bot, exc_info=True)
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
