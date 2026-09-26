"""Shared steps for the community features. Steps stay thin and call the same service code the API routes use."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pytest_bdd import given, parsers, when
from toads_api.community.demo import ANNOUNCEMENTS, PRINCIPALS, WED_CHAT, demo_store
from toads_api.community.schemas import (
    ApplicationCreate,
    ApplicationStatus,
    CurationAction,
    DiscordMessageIn,
    Post,
    Role,
    Visibility,
)
from toads_api.community.store import CommunityStore
from toads_api.rbac import Principal


@dataclass
class World:
    store: CommunityStore
    now: datetime = field(default_factory=lambda: datetime(2026, 9, 26, 18, 0, tzinfo=UTC))
    app_id: int = 0
    post: Post | None = None
    last: Any = None

    def who(self, name: str) -> Principal:
        return PRINCIPALS[name]

    def mirror(self, content: str, *, channel: int = ANNOUNCEMENTS, message_id: int = 7001) -> Post:
        post = self.store.ingest_discord_message(
            DiscordMessageIn(
                channel_id=channel, message_id=message_id, author_name="Ribbitz", content=content, created_at=self.now
            )
        )
        assert post is not None
        self.post = post
        return post

    def application(self, day: str) -> ApplicationCreate:
        return ApplicationCreate(
            character_name="Mossbeard",
            class_name="Shaman",
            spec="Restoration",
            role=Role.HEALER,
            raid_days=[day],
            experience="Cleared SSC elsewhere.",
        )


@pytest.fixture
def world() -> World:
    w = World(store=demo_store(lambda: datetime(2000, 1, 1, tzinfo=UTC)))
    w.store.clock = lambda: w.now
    return w


DAYS = {"Wednesday": "wed", "Sunday": "sun"}


@given("the demo guild")
def demo_guild(world: World) -> None:
    assert world.store.raid_days.raid_days


@given(parsers.parse("the applicant has applied for {day}"))
@when(parsers.parse("the applicant applies for {day}"))
def applicant_applies(world: World, day: str) -> None:
    world.app_id = world.store.apply(PRINCIPALS["applicant"].member_id, world.application(DAYS[day])).id


@given("a Wednesday Discord message is waiting for review")
def wed_message(world: World) -> None:
    world.mirror("Wednesday: bring flasks", channel=WED_CHAT, message_id=7200)


@given("a mirrored announcement published as public")
def published_public(world: World) -> None:
    post = world.mirror("We're recruiting healers")
    world.store.curate(world.who("global officer"), None, post.id, CurationAction.PUBLISH, Visibility.PUBLIC)


@when("the Wednesday officer declines the application")
def wed_declines(world: World) -> None:
    world.store.transition(world.who("Wednesday officer"), "wed", world.app_id, ApplicationStatus.DECLINED, "")


def advance(world: World, days: int) -> None:
    world.now += timedelta(days=days)
