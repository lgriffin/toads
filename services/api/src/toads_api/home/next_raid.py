"""The next raid on the hub home (REQ-HUB-HOME-001, REQ-HUB-HOME-006). No RBAC, web framework or storage imports.

Officers post raids as Discord scheduled events; the soonest event that has not finished is the next raid. Events are
read at most once a minute, so an officer's new or edited event shows within that (the requirement allows 5 minutes).
While Discord has no event coming up, or cannot be reached, the next raid comes from the raid days' configured start
times instead.
"""

from __future__ import annotations

import enum
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import structlog

from toads_api.discord_api import DiscordError, ScheduledEvent

log = structlog.get_logger(__name__)

# How long a read of Discord's events is reused.
CACHE_SECONDS = 60.0
# A raid without an end time counts as under way for this long after it starts, so the widget keeps showing
# tonight's raid while it runs.
RAID_LENGTH = timedelta(hours=4)
# Discord's scheduled event statuses the hub shows: scheduled and active (completed and cancelled ones never are).
_SHOWN_STATUSES = frozenset({1, 2})
_ACTIVE = 2


class Source(enum.StrEnum):
    DISCORD = "discord"
    SCHEDULE = "schedule"


@dataclass(frozen=True)
class RaidSlot:
    """A raid day's weekly start from the raid-day config."""

    day_id: str
    day_name: str
    # Monday is 0.
    weekday: int
    start: time


@dataclass(frozen=True)
class NextRaid:
    name: str
    starts_at: datetime
    ends_at: datetime | None
    raid_day_id: str | None
    raid_day_name: str | None
    source: Source
    # True once the raid has started (Discord's active status, or a scheduled start that has passed).
    under_way: bool
    # Members interested in the Discord event; None for a scheduled start.
    interested: int | None
    # The Discord event page, where members sign up.
    url: str | None


def parse_start(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


class NextRaidService:
    def __init__(
        self,
        events: Callable[[], Awaitable[list[ScheduledEvent]]],
        *,
        guild_id: int,
        slots: Sequence[RaidSlot],
        timezone: ZoneInfo,
        clock: Callable[[], float],
    ) -> None:
        self._events = events
        self._guild_id = guild_id
        self._slots = list(slots)
        self._tz = timezone
        self._clock = clock
        self._cached: tuple[float, list[ScheduledEvent]] | None = None

    async def next_raid(self) -> NextRaid | None:
        now = datetime.fromtimestamp(self._clock(), UTC)
        from_discord = self._soonest_event(await self._read_events(), now)
        return from_discord or self._soonest_slot(now)

    async def _read_events(self) -> list[ScheduledEvent]:
        """Discord's events, reused for CACHE_SECONDS. If Discord fails, the last good read stands in (or none)."""
        now = self._clock()
        if self._cached is not None and now - self._cached[0] < CACHE_SECONDS:
            return self._cached[1]
        try:
            events = await self._events()
        except DiscordError as exc:
            log.warning("next_raid.discord_unavailable", error=str(exc))
            return self._cached[1] if self._cached is not None else []
        self._cached = (now, events)
        return events

    def _day_for(self, starts_at: datetime) -> RaidSlot | None:
        weekday = starts_at.astimezone(self._tz).weekday()
        return next((s for s in self._slots if s.weekday == weekday), None)

    def _soonest_event(self, events: Sequence[ScheduledEvent], now: datetime) -> NextRaid | None:
        upcoming = [e for e in events if e.status in _SHOWN_STATUSES and (e.ends_at or e.starts_at + RAID_LENGTH) > now]
        if not upcoming:
            return None
        event = min(upcoming, key=lambda e: e.starts_at)
        day = self._day_for(event.starts_at)
        return NextRaid(
            name=event.name,
            starts_at=event.starts_at.astimezone(UTC),
            ends_at=event.ends_at.astimezone(UTC) if event.ends_at else None,
            raid_day_id=day.day_id if day else None,
            raid_day_name=day.day_name if day else None,
            source=Source.DISCORD,
            under_way=event.status == _ACTIVE or event.starts_at <= now,
            interested=event.interested,
            url=f"https://discord.com/events/{self._guild_id}/{event.event_id}",
        )

    def _soonest_slot(self, now: datetime) -> NextRaid | None:
        today = now.astimezone(self._tz).date()
        starts: list[tuple[datetime, RaidSlot]] = []
        for slot in self._slots:
            # Today through a week out covers every weekday, including one whose raid is under way right now.
            for offset in range(8):
                day = today + timedelta(days=offset)
                start = datetime.combine(day, slot.start, tzinfo=self._tz)
                if day.weekday() == slot.weekday and start + RAID_LENGTH > now:
                    starts.append((start, slot))
                    break
        if not starts:
            return None
        start, slot = min(starts, key=lambda pair: pair[0])
        return NextRaid(
            name=f"{slot.day_name} raid",
            starts_at=start.astimezone(UTC),
            ends_at=None,
            raid_day_id=slot.day_id,
            raid_day_name=slot.day_name,
            source=Source.SCHEDULE,
            under_way=start <= now,
            interested=None,
            url=None,
        )
