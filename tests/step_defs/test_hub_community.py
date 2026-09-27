"""REQ-HUB-STORY, REQ-HUB-RECRUIT, REQ-HUB-DESK, REQ-HUB-POST, REQ-HUB-SPOT: the community layer."""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from toads_api.community import recruitment
from toads_api.community.clips import parse_clip_url
from toads_api.community.demo import ANNOUNCEMENTS, GUILD_POSTS, PRINCIPALS, SUN_OFFICER_ROLE, WED_CHAT, demo_service
from toads_api.community.deps import audience_of, officer_scopes
from toads_api.community.schemas import (
    ApplicationCreate,
    ApplicationStatus,
    CurationAction,
    DiscordMessageIn,
    HighlightAction,
    HighlightCreate,
    OutboxAck,
    OutboxKind,
    Post,
    PostCreate,
    PostStatus,
    Role,
    SpotlightCreate,
    Visibility,
)
from toads_api.community.service import CommunityService, Conflict, Forbidden, NotFound
from toads_api.rbac import Principal
from toads_bot.cogs.community import NO_PINGS, Community

# ---------------------------------------------------------------- world and shared steps


@dataclass
class World:
    store: CommunityService
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

    def client(self, who: str) -> TestClient:
        """The real API over this world's service, signed in as a demo principal: for checks the routes own."""
        from conftest import community_client

        return community_client(self.store, PRINCIPALS[who])

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
    w = World(store=demo_service(lambda: datetime(2000, 1, 1, tzinfo=UTC)))
    w.store.clock = lambda: w.now
    return w


DAYS = {"Wednesday": "wed", "Sunday": "sun"}


@given("the demo guild")
def demo_guild(world: World) -> None:
    assert world.store.raid_days.day_ids


@given("the demo guild stored in the hub database")
def demo_guild_in_db(world: World) -> None:
    from conftest import sql_community_repository

    clock = world.store.clock
    world.store = demo_service(clock, sql_community_repository())  # type: ignore[arg-type]


@when("the API restarts")
def api_restarts(world: World) -> None:
    from toads_api.community.sql_repository import SqlCommunityRepository

    repo = world.store.repo
    assert isinstance(repo, SqlCommunityRepository)
    # A new service and repository over the same database: nothing carried over in memory.
    world.store = CommunityService(
        repo=SqlCommunityRepository(repo.db),
        config=world.store.config,
        raid_days=world.store.raid_days,
        clock=world.store.clock,
    )


@then("the application is still declined with its full history")
def still_declined(world: World) -> None:
    app = world.store.repo.get_application(world.app_id)
    assert app is not None
    assert app.status is ApplicationStatus.DECLINED
    assert [(e.from_status, e.to_status) for e in app.events] == [
        (None, ApplicationStatus.APPLIED),
        (ApplicationStatus.APPLIED, ApplicationStatus.DECLINED),
    ]
    assert [e.actor_name for e in app.events] == ["Newtonian", "Croakley"]


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
    world.store.curate(world.who("global officer").member_id, None, post.id, CurationAction.PUBLISH, Visibility.PUBLIC)


@when("the Wednesday officer declines the application")
def wed_declines(world: World) -> None:
    world.store.transition(
        world.who("Wednesday officer").member_id, "wed", world.app_id, ApplicationStatus.DECLINED, ""
    )


def advance(world: World, days: int) -> None:
    world.now += timedelta(days=days)


FEATURES = Path(__file__).resolve().parents[1] / "features"
for name in ("hub_story", "hub_recruit", "hub_desk", "hub_post", "hub_spot"):
    scenarios(str(FEATURES / f"{name}.feature"))


def jobs(world: World, kind: OutboxKind) -> list[dict[str, object]]:
    return [j.payload for j in world.store.pending_jobs() if j.kind is kind]


# --------------------------------------------------------------------- story


@given("a public post, a guild post, a public highlight and a published spotlight")
def published_things(world: World) -> None:
    gm, s = world.who("global officer").member_id, world.store
    s.create_post(gm, None, PostCreate(title="Hello world", body="We raid twice a week", visibility=Visibility.PUBLIC))
    s.create_post(gm, None, PostCreate(title="Inside news", body="Loot rules", visibility=Visibility.GUILD))
    hl = s.submit_highlight(4, HighlightCreate(title="Vashj kill", url="https://youtu.be/dQw4w9WgXcQ"))
    s.review_highlight(gm, hl.id, HighlightAction.PUBLISH_PUBLIC)
    sp = s.create_spotlight(
        gm, SpotlightCreate(member_id=4, character_name="Hopscotch", class_name="Rogue", headline="Kicks", body="Lots")
    )
    s.decide_consent(4, sp.id, grant=True)
    s.publish_spotlight(gm, sp.id)


@given("a Discord post waiting for review, a submitted highlight and a spotlight awaiting consent")
def unpublished_things(world: World) -> None:
    gm, s = world.who("global officer").member_id, world.store
    world.mirror("Raid at 19:00")
    s.submit_highlight(4, HighlightCreate(title="Wipe", url="https://streamable.com/abc123"))
    s.create_spotlight(
        gm, SpotlightCreate(member_id=4, character_name="Hopscotch", class_name="Rogue", headline="Kicks", body="Lots")
    )


@when("a visitor opens the public story", target_fixture="story")
def open_story(world: World) -> object:
    return world.store.public_story()


@then("they see the progression and the recruitment needs")
def sees_progress(story: SimpleNamespace) -> None:
    assert story.progression and story.needs


@then("they see the public post, the public highlight and the spotlight")
def sees_public(story: SimpleNamespace) -> None:
    assert [p.title for p in story.posts] == ["Hello world"]
    assert [h.title for h in story.highlights] == ["Vashj kill"]
    assert [s.headline for s in story.spotlights] == ["Kicks"]


@then("they see nothing that was published only to the guild")
def sees_no_guild(story: SimpleNamespace) -> None:
    assert all(p.visibility is Visibility.PUBLIC for p in story.posts)


@then("the story has no posts, highlights or spotlights")
def story_empty(story: SimpleNamespace) -> None:
    assert (story.posts, story.highlights, story.spotlights) == ([], [], [])


# --------------------------------------------------------------- recruitment


@then("the Wednesday officer and the global officer see the application")
def wed_and_gm_see(world: World) -> None:
    assert [a.id for a in world.store.applications_for("wed")] == [world.app_id]
    assert [a.id for a in world.store.applications_for(None)] == [world.app_id]


@then("the Sunday officer does not")
def sun_does_not(world: World) -> None:
    assert world.store.applications_for("sun") == []
    with pytest.raises(NotFound):
        world.store.transition(
            world.who("Sunday officer").member_id, "sun", world.app_id, ApplicationStatus.DECLINED, ""
        )


@given("the Wednesday officer has opened an interview room")
@when("the Wednesday officer opens an interview room")
def open_room(world: World) -> None:
    world.store.open_interview_room(world.who("Wednesday officer").member_id, "wed", world.app_id)
    [job] = [j for j in world.store.pending_jobs() if j.kind is OutboxKind.CREATE_INTERVIEW_ROOM]
    world.store.ack(job.id, OutboxAck(channel_id=6001))


@then("the application is being interviewed")
def interviewing(world: World) -> None:
    assert world.store.repo.get_application(world.app_id).status is ApplicationStatus.INTERVIEWING


@then("the bot is asked for a room for the applicant with the Wednesday and global officer roles only")
def room_job(world: World) -> None:
    [job] = [j for j in world.store.repo.jobs() if j.kind is OutboxKind.CREATE_INTERVIEW_ROOM]
    assert job.payload["discord_user_id"] == 10_005
    assert job.payload["officer_role_ids"] == [12, 900]
    assert SUN_OFFICER_ROLE not in job.payload["officer_role_ids"]  # type: ignore[operator]


def _bot(**kw: object) -> Community:
    return Community(MagicMock(), AsyncMock(), guild_id=1, mirror_channel_ids=set(), post_to_channels=True, **kw)  # type: ignore[arg-type]


@then("the bot creates a channel hidden from everyone else")
def bot_creates(world: World) -> None:
    [job] = [j for j in world.store.repo.jobs() if j.kind is OutboxKind.CREATE_INTERVIEW_ROOM]
    guild = MagicMock()
    guild.default_role = discord.Object(id=1)
    guild.me = discord.Object(id=99)
    guild.get_member.return_value = MagicMock(id=10_005, mention="<@10005>")
    guild.get_role.side_effect = lambda rid: discord.Object(id=rid)
    guild.get_channel.return_value = None
    created = MagicMock(id=6001)
    created.send = AsyncMock()
    guild.create_text_channel = AsyncMock(return_value=created)
    asyncio.run(_bot().open_interview_room(guild, dict(job.payload)))
    overwrites = guild.create_text_channel.await_args.kwargs["overwrites"]
    assert {k.id: v.view_channel for k, v in overwrites.items()} == {
        1: False,
        10_005: True,
        12: True,
        900: True,
        99: True,
    }


@then("the bot is asked to lock the interview room")
def lock_job(world: World) -> None:
    [payload] = jobs(world, OutboxKind.LOCK_INTERVIEW_ROOM)
    assert payload["channel_id"] == 6001


@then("the bot leaves the applicant able to read but not post")
def bot_locks(world: World) -> None:
    [payload] = jobs(world, OutboxKind.LOCK_INTERVIEW_ROOM)
    channel = MagicMock(spec=discord.TextChannel)
    applicant, officers = discord.Object(id=10_005), discord.Object(id=12)
    channel.overwrites = {applicant: discord.PermissionOverwrite(send_messages=True), officers: "kept"}
    channel.edit = AsyncMock()
    guild = MagicMock()
    guild.get_channel.return_value = channel
    asyncio.run(_bot().lock_interview_room(guild, dict(payload)))
    new = channel.edit.await_args.kwargs["overwrites"]
    assert (new[applicant].view_channel, new[applicant].send_messages) == (True, False)
    assert new[officers] == "kept"


@then("accepting straight from applied is refused with 409")
def accept_refused(world: World) -> None:
    with pytest.raises(Conflict) as e:
        world.store.transition(
            world.who("Wednesday officer").member_id, "wed", world.app_id, ApplicationStatus.ACCEPTED, ""
        )
    assert e.value.status_code == 409


@then("every pair of statuses outside the pipeline is refused")
def pipeline_closed(world: World) -> None:
    allowed = {
        (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING),
        (ApplicationStatus.APPLIED, ApplicationStatus.DECLINED),
        (ApplicationStatus.APPLIED, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.TRIAL_OFFERED),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.DECLINED),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.WITHDRAWN),
        (ApplicationStatus.TRIAL_OFFERED, ApplicationStatus.ACCEPTED),
        (ApplicationStatus.TRIAL_OFFERED, ApplicationStatus.DECLINED),
        (ApplicationStatus.TRIAL_OFFERED, ApplicationStatus.WITHDRAWN),
    }
    for a, b in itertools.product(ApplicationStatus, repeat=2):
        assert recruitment.can_transition(a, b) is ((a, b) in allowed)


@then("a second application is refused with 409")
def second_refused(world: World) -> None:
    with pytest.raises(Conflict):
        world.store.apply(5, world.application("wed"))


@then("a new application 29 days later is refused with 409")
def day_29(world: World) -> None:
    advance(world, 29)
    with pytest.raises(Conflict):
        world.store.apply(5, world.application("wed"))


@then("a new application 31 days later is accepted")
def day_31(world: World) -> None:
    world.now += timedelta(days=2)
    assert world.store.apply(5, world.application("wed")).status is ApplicationStatus.APPLIED


@then(
    "the application form's fields are character, class, spec, role, raid days, experience, availability and a "
    "Warcraft Logs link"
)
def form_fields() -> None:
    assert set(ApplicationCreate.model_fields) == {
        "character_name",
        "class_name",
        "spec",
        "role",
        "raid_days",
        "experience",
        "availability",
        "logs_url",
    }


@then("a Warcraft Logs link must be an https link to warcraftlogs.com")
def logs_link() -> None:
    assert recruitment.valid_logs_url("https://fresh.warcraftlogs.com/character/eu/spineshatter/x")
    assert not recruitment.valid_logs_url("http://fresh.warcraftlogs.com/character/eu/spineshatter/x")
    assert not recruitment.valid_logs_url("https://warcraftlogs.com.evil.example/x")


# ---------------------------------------------------------------------- desk


@then("the Wednesday officer's desk shows no applications and one post to curate")
def wed_desk(world: World) -> None:
    desk = world.store.desk(officer_scopes(world.who("Wednesday officer")))
    assert (desk.applications_waiting, desk.posts_to_curate) == (0, 1)


@then("the Sunday officer's desk shows one application")
def sun_desk(world: World) -> None:
    desk = world.store.desk(officer_scopes(world.who("Sunday officer")))
    assert (desk.applications_waiting, desk.posts_to_curate) == (1, 0)


# --------------------------------------------------------------------- posts


@when("the bot mirrors an announcement")
def mirrors(world: World) -> None:
    world.mirror("Raid moved to 19:00")


@then("members do not see it")
def members_do_not_see(world: World) -> None:
    assert world.store.feed(audience_of(world.who("Wednesday raider"))) == []


@when("the global officer publishes it to the guild")
def gm_publishes(world: World) -> None:
    if world.post is not None:
        world.store.curate(
            world.who("global officer").member_id, None, world.post.id, CurationAction.PUBLISH, Visibility.GUILD
        )
    else:
        [hl] = world.store.repo.highlights()
        world.store.review_highlight(world.who("global officer").member_id, hl.id, HighlightAction.PUBLISH_GUILD)


@then("members see it marked as from Discord")
def members_see(world: World) -> None:
    [post] = world.store.feed(audience_of(world.who("Sunday trial")))
    assert post.origin.value == "discord"


@when("the global officer writes a post and ticks also post to Discord")
def gm_writes(world: World) -> None:
    world.post = world.store.create_post(
        world.who("global officer").member_id,
        None,
        PostCreate(title="Patch day", body="No raid", publish_to_discord=True),
    )


@then("the bot is asked to post it to the guild posts channel")
def post_job(world: World) -> None:
    assert jobs(world, OutboxKind.POST_MESSAGE) == [{"post_id": world.post.id, "channel_id": GUILD_POSTS}]  # type: ignore[union-attr]


@when("the bot reports the Discord message it sent")
def bot_acks(world: World) -> None:
    [job] = [j for j in world.store.pending_jobs() if j.kind is OutboxKind.POST_MESSAGE]
    world.store.ack(job.id, OutboxAck(message_id=8001))


@when("the global officer edits the post")
def gm_edits(world: World) -> None:
    assert world.post is not None
    world.store.update_post(
        world.who("global officer").member_id, None, world.post.id, PostCreate(title="Patch day", body="Thu")
    )


@then("the bot is asked to edit that Discord message")
def edit_job(world: World) -> None:
    [payload] = jobs(world, OutboxKind.EDIT_MESSAGE)
    assert payload["message_id"] == 8001


@when("its author edits it in Discord")
def author_edits(world: World) -> None:
    world.mirror("Actually, something else entirely")


@then("it is waiting for review again and flagged as edited")
def back_to_review(world: World) -> None:
    assert world.post is not None
    assert (world.post.status, world.post.edited_since_review) == (PostStatus.PENDING_REVIEW, True)


@then("the public story does not show it")
def not_on_story(world: World) -> None:
    story = world.store.public_story()
    assert story.posts == [] and story.spotlights == []


@when("its author deletes it in Discord")
def author_deletes(world: World) -> None:
    assert world.post is not None and world.post.discord_message_id is not None
    world.store.discord_message_deleted(world.post.discord_message_id)


@then("nobody sees it on the hub")
def nobody_sees(world: World) -> None:
    assert world.store.feed(audience_of(world.who("global officer"))) == []
    assert world.store.public_story().posts == []


@when('the bot mirrors "@everyone raid in 5 @here"')
def mirrors_ping(world: World) -> None:
    world.mirror("@everyone raid in 5 @here")


@then("the stored post cannot ping anyone")
def no_ping_stored(world: World) -> None:
    assert world.post is not None
    assert "@everyone" not in world.post.body and "@here" not in world.post.body


@then("the bot sends officer posts with every mention type switched off")
def no_ping_sent() -> None:
    assert (NO_PINGS.everyone, NO_PINGS.users, NO_PINGS.roles, NO_PINGS.replied_user) == (False, False, False, False)


@then("the Wednesday officer cannot publish it as public")
def wed_not_public(world: World) -> None:
    assert world.post is not None
    # A tier check, so it is the route layer's to refuse: go through the real API.
    r = world.client("Wednesday officer").post(
        f"/api/days/wed/admin/curation/{world.post.id}", json={"action": "publish", "visibility": "public"}
    )
    assert r.status_code == 403
    assert world.post.status is PostStatus.PENDING_REVIEW


@then("the Sunday officer cannot see or curate it")
def sun_cannot(world: World) -> None:
    assert world.post is not None
    assert world.store.curation_queue("sun") == []
    with pytest.raises(NotFound):
        world.store.curate(world.who("Sunday officer").member_id, "sun", world.post.id, CurationAction.PUBLISH, None)


@then("a message from an unlisted channel is refused")
def unlisted(world: World) -> None:
    with pytest.raises(Forbidden):
        world.mirror("officer chat", channel=987654)


# ---------------------------------------------------------------- highlights


@then("a YouTube, a Twitch and a Streamable link are accepted as provider and clip id")
def clips_ok() -> None:
    for url, provider, clip in [
        ("https://youtu.be/dQw4w9WgXcQ", "youtube", "dQw4w9WgXcQ"),
        ("https://clips.twitch.tv/BraveTinyToad", "twitch", "BraveTinyToad"),
        ("https://streamable.com/abc123", "streamable", "abc123"),
    ]:
        ref = parse_clip_url(url)
        assert ref is not None and (ref.provider.value, ref.clip_id) == (provider, clip)


@then("a link to any other host, or over http, is refused")
def clips_refused() -> None:
    for url in ("https://evil.example/watch?v=dQw4w9WgXcQ", "http://youtu.be/dQw4w9WgXcQ", "javascript:alert(1)"):
        assert parse_clip_url(url) is None


@when("the raider submits a clip")
def raider_submits(world: World) -> None:
    world.store.submit_highlight(4, HighlightCreate(title="Vashj", url="https://youtu.be/dQw4w9WgXcQ"))


@then("nobody sees it yet")
def nobody_sees_clip(world: World) -> None:
    assert world.store.highlights_for(audience_of(world.who("global officer"))) == []


@then("members see it and the public story does not")
def members_see_clip(world: World) -> None:
    assert len(world.store.highlights_for(audience_of(world.who("Sunday trial")))) == 1
    assert world.store.public_story().highlights == []


@when("the global officer writes a spotlight about the raider")
def gm_spotlight(world: World) -> None:
    world.last = world.store.create_spotlight(
        world.who("global officer").member_id,
        SpotlightCreate(member_id=4, character_name="Hopscotch", class_name="Rogue", headline="Kicks", body="Lots"),
    )


@then("publishing it is refused with 409")
def spotlight_refused(world: World) -> None:
    with pytest.raises(Conflict):
        world.store.publish_spotlight(world.who("global officer").member_id, world.last.id)


@when("the raider agrees to it")
def raider_agrees(world: World) -> None:
    world.store.decide_consent(4, world.last.id, grant=True)


@when("the global officer publishes it")
def gm_publishes_spotlight(world: World) -> None:
    world.store.publish_spotlight(world.who("global officer").member_id, world.last.id)


@then("the public story shows it")
def story_shows(world: World) -> None:
    assert [s.headline for s in world.store.public_story().spotlights] == ["Kicks"]


@when("the raider withdraws agreement")
def raider_withdraws(world: World) -> None:
    world.store.decide_consent(4, world.last.id, grant=False)
