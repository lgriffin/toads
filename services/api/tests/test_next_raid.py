"""The next raid on the hub home: Discord's scheduled events first, the raid days' start times as the fallback."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import anyio
import pytest
from toads_api.discord_api import DiscordError, ScheduledEvent
from toads_api.home.next_raid import CACHE_SECONDS, NextRaid, NextRaidService, RaidSlot, Source, parse_start

from conftest import Hub

PARIS = ZoneInfo("Europe/Paris")
# Monday 28 September 2026, 12:00 server time.
MONDAY_NOON = datetime(2026, 9, 28, 12, 0, tzinfo=PARIS)
WED = RaidSlot("wed", "Wednesday", 2, time(19, 30))
SUN = RaidSlot("sun", "Sunday", 6, time(19, 0))


def _event(event_id: int, start: datetime, *, status: int = 1, end: datetime | None = None) -> ScheduledEvent:
    return ScheduledEvent(event_id, f"Raid {event_id}", start, end, status, 10)


class Events:
    def __init__(self, *events: ScheduledEvent) -> None:
        self.events = list(events)
        self.reads = 0
        self.fail = False

    async def __call__(self) -> list[ScheduledEvent]:
        self.reads += 1
        if self.fail:
            raise DiscordError("Discord down")
        return list(self.events)


def _service(events: Events, now: list[float], slots: tuple[RaidSlot, ...] = (WED, SUN)) -> NextRaidService:
    return NextRaidService(events, guild_id=77, slots=slots, timezone=PARIS, clock=lambda: now[0])


def _next(svc: NextRaidService) -> NextRaid | None:
    return anyio.run(svc.next_raid)


def test_soonest_event_wins_and_is_matched_to_its_raid_day() -> None:
    wed = datetime(2026, 9, 30, 20, 0, tzinfo=PARIS)
    events = Events(_event(2, wed + timedelta(days=4)), _event(1, wed))
    raid = _next(_service(events, [MONDAY_NOON.timestamp()]))
    assert raid is not None
    assert (raid.name, raid.source, raid.raid_day_id, raid.interested) == ("Raid 1", Source.DISCORD, "wed", 10)
    assert raid.starts_at == wed.astimezone(UTC) and raid.starts_at.tzinfo is UTC
    assert raid.url == "https://discord.com/events/77/1"
    assert not raid.under_way


def test_finished_and_cancelled_events_are_skipped() -> None:
    now = MONDAY_NOON
    events = Events(
        _event(1, now - timedelta(hours=6)),  # started six hours ago, no end: over
        _event(2, now + timedelta(hours=1), status=4),  # cancelled
        _event(3, now - timedelta(hours=1), end=now - timedelta(minutes=5)),  # ended
        _event(4, now - timedelta(hours=1), status=2),  # under way
    )
    raid = _next(_service(events, [now.timestamp()]))
    assert raid is not None and raid.name == "Raid 4" and raid.under_way


def test_events_are_read_at_most_once_a_minute() -> None:
    now = [MONDAY_NOON.timestamp()]
    events = Events(_event(1, MONDAY_NOON + timedelta(days=2)))
    svc = _service(events, now)
    _next(svc)
    _next(svc)
    assert events.reads == 1
    now[0] += CACHE_SECONDS
    _next(svc)
    assert events.reads == 2


def test_discord_failure_keeps_the_last_read() -> None:
    now = [MONDAY_NOON.timestamp()]
    events = Events(_event(1, MONDAY_NOON + timedelta(days=2)))
    svc = _service(events, now)
    assert _next(svc) is not None
    events.fail = True
    now[0] += CACHE_SECONDS * 5
    raid = _next(svc)
    assert raid is not None and raid.source is Source.DISCORD


def test_without_events_the_schedule_gives_the_next_raid() -> None:
    raid = _next(_service(Events(), [MONDAY_NOON.timestamp()]))
    assert raid is not None
    assert (raid.name, raid.source, raid.raid_day_id, raid.url) == ("Wednesday raid", Source.SCHEDULE, "wed", None)
    assert raid.starts_at == datetime(2026, 9, 30, 19, 30, tzinfo=PARIS).astimezone(UTC)


def test_discord_down_with_nothing_read_falls_back_to_the_schedule() -> None:
    events = Events()
    events.fail = True
    raid = _next(_service(events, [MONDAY_NOON.timestamp()]))
    assert raid is not None and raid.source is Source.SCHEDULE


def test_tonights_raid_shows_while_it_runs() -> None:
    wednesday_evening = datetime(2026, 9, 30, 21, 0, tzinfo=PARIS)
    raid = _next(_service(Events(), [wednesday_evening.timestamp()]))
    assert raid is not None and raid.raid_day_id == "wed" and raid.under_way


def test_schedule_follows_daylight_saving() -> None:
    # Clocks go back on Sunday 25 October 2026; the Sunday raid is still 19:00 server time.
    saturday = datetime(2026, 10, 24, 12, 0, tzinfo=PARIS)
    raid = _next(_service(Events(), [saturday.timestamp()], slots=(SUN,)))
    assert raid is not None
    assert raid.starts_at == datetime(2026, 10, 25, 18, 0, tzinfo=UTC)


def test_no_events_and_no_start_times_means_no_next_raid() -> None:
    assert _next(_service(Events(), [MONDAY_NOON.timestamp()], slots=())) is None


@pytest.mark.parametrize(("value", "expected"), [("19:30", time(19, 30)), ("00:05", time(0, 5))])
def test_parse_start(value: str, expected: time) -> None:
    assert parse_start(value) == expected


def test_scheduled_event_from_discord() -> None:
    event = ScheduledEvent.from_api(
        {
            "id": "123",
            "name": "Gruul",
            "scheduled_start_time": "2026-09-30T18:30:00+00:00",
            "scheduled_end_time": None,
            "status": 1,
            "user_count": 21,
        }
    )
    assert (event.event_id, event.name, event.interested, event.ends_at) == (123, "Gruul", 21, None)
    assert event.starts_at == datetime(2026, 9, 30, 18, 30, tzinfo=UTC)
    naive = ScheduledEvent.from_api(
        {**{"id": "1", "name": "x", "status": 2}, "scheduled_start_time": "2026-09-30T18:30:00"}
    )
    assert naive.starts_at.tzinfo is UTC and naive.interested is None


def test_next_raid_route(hub: Hub) -> None:
    assert hub.get("/api/home/next-raid", None).status_code == 401
    sid = hub.login(hub.user(("wed", "raider")))
    start = datetime.fromtimestamp(hub.now, UTC) + timedelta(days=1)
    hub.fake.add_event(55, "Magtheridon", start, interested=None)
    raid = hub.get("/api/home/next-raid", sid).json()["raid"]
    assert (raid["name"], raid["source"], raid["interested"]) == ("Magtheridon", "discord", None)
    assert datetime.fromisoformat(raid["starts_at"]) == start


def test_discord_errors_on_the_route_fall_back_to_the_schedule(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    hub.fake.events_down = True
    raid = hub.get("/api/home/next-raid", sid).json()["raid"]
    assert raid["source"] == "schedule" and raid["raid_day_id"] == "wed"
