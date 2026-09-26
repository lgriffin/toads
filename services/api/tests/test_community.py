"""Community routes: recruitment and interview rooms, two-way posts, highlight reels, spotlights, the bot's routes."""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from toads_api.community.demo import ANNOUNCEMENTS, GUILD_POSTS, PRINCIPALS, WED_CHAT, demo_store
from toads_api.community.deps import get_store
from toads_api.community.settings import CommunitySettings, get_community_settings
from toads_api.community.store import CommunityStore
from toads_api.main import create_app
from toads_api.rbac import Permission, Principal, can
from toads_api.rbac.deps import get_principal

TOKEN = "test-only-not-a-secret"  # noqa: S105
BOT = {"Authorization": f"Bearer {TOKEN}"}


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 26, 18, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(clock: Clock) -> CommunityStore:
    return demo_store(clock)


@pytest.fixture
def as_(store: CommunityStore) -> Iterator[Any]:
    """as_("Wednesday officer") -> a TestClient signed in as that demo principal; as_(None) is anonymous."""

    def make(who: str | Principal | None) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_store] = lambda: store
        app.dependency_overrides[get_community_settings] = lambda: CommunitySettings(hub_service_token=SecretStr(TOKEN))
        principal = PRINCIPALS[who] if isinstance(who, str) else who
        if principal is not None:

            async def _p() -> Principal:
                return principal

            app.dependency_overrides[get_principal] = _p
        return TestClient(app)

    yield make


def _discord_msg(channel: int, message: int, content: str) -> dict[str, Any]:
    return {
        "channel_id": channel,
        "message_id": message,
        "author_name": "Ribbitz",
        "content": content,
        "created_at": "2026-09-26T17:00:00Z",
    }


APPLICATION = {
    "character_name": "Mossbeard",
    "class_name": "Shaman",
    "spec": "Restoration",
    "role": "Healer",
    "raid_days": ["wed"],
    "experience": "Cleared SSC on another server; happy to trial.",
    "availability": "Wednesdays and most Sundays",
    "logs_url": "https://fresh.warcraftlogs.com/character/eu/spineshatter/mossbeard",
}


# --------------------------------------------------------------- RBAC matrix

# Every community route with the permission it needs. A new route without a row here fails
# test_every_community_route_is_in_the_matrix, so no route ships without a permission (REQ-HUB-DAY-021).
ROUTES: list[tuple[str, str, Permission]] = [
    ("GET", "/api/posts", Permission.VIEW_GUILD_RAIDS),
    ("GET", "/api/highlights", Permission.VIEW_GUILD_RAIDS),
    ("POST", "/api/highlights", Permission.SUBMIT_HIGHLIGHT),
    ("POST", "/api/applications", Permission.APPLY),
    ("GET", "/api/applications/mine", Permission.APPLY),
    ("POST", "/api/applications/{app_id}/withdraw", Permission.APPLY),
    ("GET", "/api/me/spotlights", Permission.VIEW_GUILD_RAIDS),
    ("POST", "/api/me/spotlights/{sp_id}/consent", Permission.VIEW_GUILD_RAIDS),
    ("GET", "/api/desk", Permission.VIEW_GUILD_RAIDS),
    ("PUT", "/api/admin/recruitment/needs", Permission.MANAGE_RECRUITMENT),
    ("GET", "/api/admin/highlights", Permission.MANAGE_HIGHLIGHTS),
    ("POST", "/api/admin/highlights/{hl_id}/review", Permission.MANAGE_HIGHLIGHTS),
    ("GET", "/api/admin/spotlights", Permission.MANAGE_HIGHLIGHTS),
    ("POST", "/api/admin/spotlights", Permission.MANAGE_HIGHLIGHTS),
    ("POST", "/api/admin/spotlights/{sp_id}/publish", Permission.MANAGE_HIGHLIGHTS),
    ("POST", "/api/admin/spotlights/{sp_id}/retire", Permission.MANAGE_HIGHLIGHTS),
] + [
    (method, f"{prefix}{path}", perm)
    for prefix in ("/api/admin", "/api/days/{day}/admin")
    for method, path, perm in [
        ("GET", "/applications", Permission.MANAGE_RECRUITMENT),
        ("POST", "/applications/{app_id}/transition", Permission.MANAGE_RECRUITMENT),
        ("POST", "/applications/{app_id}/interview-room", Permission.MANAGE_RECRUITMENT),
        ("GET", "/curation", Permission.MANAGE_POSTS),
        ("POST", "/curation/{post_id}", Permission.MANAGE_POSTS),
        ("POST", "/posts", Permission.MANAGE_POSTS),
        ("PUT", "/posts/{post_id}", Permission.MANAGE_POSTS),
    ]
]
PUBLIC = {("GET", "/api/public/story"), ("GET", "/api/public/recruitment")}
BOT_ROUTES = {
    ("GET", "/api/bot/outbox"),
    ("POST", "/api/bot/outbox/{job_id}/ack"),
    ("POST", "/api/bot/discord-messages"),
    ("POST", "/api/bot/discord-messages/{message_id}/deleted"),
}


def test_every_community_route_is_in_the_matrix() -> None:
    core = {("GET", "/api/me"), ("POST", "/api/days/{day}/admin/sync")}
    # Read from the OpenAPI schema: FastAPI no longer flattens included routers into app.routes.
    paths = create_app().openapi()["paths"]
    served = {(method.upper(), path) for path, ops in paths.items() for method in ops}
    assert served - core == {(m, p) for m, p, _ in ROUTES} | PUBLIC | BOT_ROUTES


def _concrete(path: str, day: str) -> str:
    return (
        path.replace("{day}", day)
        .replace("{app_id}", "999999")
        .replace("{post_id}", "999999")
        .replace("{hl_id}", "999999")
        .replace("{sp_id}", "999999")
    )


@pytest.mark.parametrize(
    ("who", "route", "day"),
    [(w, r, d) for w, r, d in itertools.product(PRINCIPALS, ROUTES, ("wed", "sun")) if "{day}" in r[1] or d == "wed"],
    ids=lambda v: v if isinstance(v, str) else f"{v[0]} {v[1]}",
)
def test_route_permission_matrix(as_: Any, who: str, route: tuple[str, str, Permission], day: str) -> None:
    """(tier x raid day x endpoint): allowed exactly when the permission table says so, sibling days included."""
    method, path, permission = route
    scoped_day = day if "{day}" in path else None
    allowed = can(PRINCIPALS[who], permission, scoped_day)
    r = as_(who).request(method, _concrete(path, day), json={})
    if allowed:
        # Past the permission check: the empty body or the made-up id fails later, never with 401/403...
        # ...except the desk, which is additionally officers-only.
        if path == "/api/desk" and who in {"Wednesday raider", "applicant", "Sunday trial"}:
            assert r.status_code == 403
        else:
            assert r.status_code not in (401, 403), r.text
    else:
        assert r.status_code == 403, r.text


@pytest.mark.parametrize(("method", "path", "_perm"), ROUTES)
def test_anonymous_is_refused_everywhere_but_public(as_: Any, method: str, path: str, _perm: Permission) -> None:
    assert as_(None).request(method, _concrete(path, "wed"), json={}).status_code == 401


@pytest.mark.security
@pytest.mark.parametrize(("method", "path"), sorted(BOT_ROUTES))
@pytest.mark.parametrize(
    "header",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": TOKEN},
        {"Authorization": "Bearer tökén".encode("latin-1")},
    ],
)
def test_bot_routes_need_the_service_token(as_: Any, method: str, path: str, header: dict[str, Any]) -> None:
    r = as_("global officer").request(
        method, _concrete(path, "wed").replace("{job_id}", "1").replace("{message_id}", "1"), json={}, headers=header
    )
    assert r.status_code == 401


@pytest.mark.security
def test_bot_routes_refuse_everything_when_no_token_is_configured(as_: Any, store: CommunityStore) -> None:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_community_settings] = lambda: CommunitySettings(hub_service_token=SecretStr(""))
    assert TestClient(app).get("/api/bot/outbox", headers={"Authorization": "Bearer "}).status_code == 401


# ---------------------------------------------------------------- public story


def test_public_story_needs_no_login(as_: Any) -> None:
    r = as_(None).get("/api/public/story")
    assert r.status_code == 200
    body = r.json()
    assert body["guild"] == "Toads"
    assert body["needs"][0]["class_name"] == "Shaman"
    assert body["progression"] == [{"zone": "Serpentshrine Cavern", "killed": 5, "total": 6}]


def test_public_story_shows_only_public_posts(as_: Any) -> None:
    officer = as_("global officer")
    officer.post("/api/admin/posts", json={"title": "Guild only", "body": "Inside news", "visibility": "guild"})
    officer.post("/api/admin/posts", json={"title": "Hello world", "body": "We're recruiting", "visibility": "public"})
    as_("Wednesday officer").post("/api/days/wed/admin/posts", json={"title": "Wed only", "body": "Bring pots"})
    titles = [p["title"] for p in as_(None).get("/api/public/story").json()["posts"]]
    assert titles == ["Hello world"]


# ------------------------------------------------------------ two-way posts


def test_discord_message_waits_for_an_officer(as_: Any) -> None:
    bot = as_(None)
    r = bot.post(
        "/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7001, "Raid moved to 19:00"), headers=BOT
    )
    assert r.status_code == 202
    assert r.json()["status"] == "pending_review"
    raider = as_("Wednesday raider")
    assert raider.get("/api/posts").json() == []

    officer = as_("global officer")
    queue = officer.get("/api/admin/curation").json()
    assert [p["title"] for p in queue] == ["Raid moved to 19:00"]
    officer.post(f"/api/admin/curation/{queue[0]['id']}", json={"action": "publish", "visibility": "guild"})
    feed = raider.get("/api/posts").json()
    assert [(p["title"], p["origin"]) for p in feed] == [("Raid moved to 19:00", "discord")]


def test_raid_day_channel_is_curated_by_that_days_officers(as_: Any) -> None:
    as_(None).post("/api/bot/discord-messages", json=_discord_msg(WED_CHAT, 7002, "Wed: flasks please"), headers=BOT)
    assert as_("global officer").get("/api/admin/curation").json() == []
    queue = as_("Wednesday officer").get("/api/days/wed/admin/curation").json()
    assert len(queue) == 1
    post_id = queue[0]["id"]
    assert as_("Sunday officer").get("/api/days/wed/admin/curation").status_code == 403
    assert as_("Sunday officer").get("/api/days/sun/admin/curation").json() == []
    # A post from another day's queue is reported missing, not forbidden, so ids do not leak.
    r = as_("Sunday officer").post(f"/api/days/sun/admin/curation/{post_id}", json={"action": "publish"})
    assert r.status_code == 404
    # Raid-day officers cannot push anything to the public story.
    r = as_("Wednesday officer").post(
        f"/api/days/wed/admin/curation/{post_id}", json={"action": "publish", "visibility": "public"}
    )
    assert r.status_code == 403
    r = as_("Wednesday officer").post(f"/api/days/wed/admin/curation/{post_id}", json={"action": "publish"})
    assert r.json()["status"] == "published"
    assert [p["title"] for p in as_("Wednesday raider").get("/api/posts").json()] == ["Wed: flasks please"]
    assert as_("Sunday trial").get("/api/posts").json() == []


@pytest.mark.security
def test_unmirrored_channel_is_refused(as_: Any) -> None:
    r = as_(None).post("/api/bot/discord-messages", json=_discord_msg(987654, 1, "officer chat leak"), headers=BOT)
    assert r.status_code == 403


@pytest.mark.security
def test_mass_mentions_are_defanged(as_: Any) -> None:
    r = as_(None).post(
        "/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7003, "@everyone raid now @HERE"), headers=BOT
    )
    assert "@everyone" not in r.json()["body"]
    assert "@HERE" not in r.json()["body"]


def test_edit_after_review_sends_public_post_back_to_review(as_: Any) -> None:
    bot, officer = as_(None), as_("global officer")
    post = bot.post("/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7004, "Recruiting!"), headers=BOT)
    officer.post(f"/api/admin/curation/{post.json()['id']}", json={"action": "publish", "visibility": "public"})
    assert [p["title"] for p in as_(None).get("/api/public/story").json()["posts"]] == ["Recruiting!"]
    edited = bot.post(
        "/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7004, "Something else"), headers=BOT
    )
    assert edited.json()["status"] == "pending_review"
    assert edited.json()["edited_since_review"] is True
    assert as_(None).get("/api/public/story").json()["posts"] == []


def test_edit_after_review_keeps_guild_post_but_flags_it(as_: Any) -> None:
    bot, officer = as_(None), as_("global officer")
    post = bot.post("/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7005, "Tonight"), headers=BOT)
    officer.post(f"/api/admin/curation/{post.json()['id']}", json={"action": "publish"})
    edited = bot.post("/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7005, "Tonight 19:30"), headers=BOT)
    assert edited.json()["status"] == "published"
    assert edited.json()["edited_since_review"] is True


def test_deleting_in_discord_takes_the_post_down(as_: Any) -> None:
    bot, officer = as_(None), as_("global officer")
    post = bot.post("/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7006, "Oops"), headers=BOT)
    officer.post(f"/api/admin/curation/{post.json()['id']}", json={"action": "publish"})
    assert bot.post("/api/bot/discord-messages/7006/deleted", headers=BOT).status_code == 204
    assert as_("Wednesday raider").get("/api/posts").json() == []


def test_hub_post_goes_out_to_discord_and_edits_follow(as_: Any, store: CommunityStore) -> None:
    officer, bot = as_("global officer"), as_(None)
    post = officer.post(
        "/api/admin/posts", json={"title": "Patch day", "body": "No raid Wednesday", "publish_to_discord": True}
    ).json()
    jobs = bot.get("/api/bot/outbox", headers=BOT).json()
    assert [(j["job"]["kind"], j["job"]["payload"]["channel_id"]) for j in jobs] == [("post_message", GUILD_POSTS)]
    assert jobs[0]["post"]["title"] == "Patch day"
    bot.post(f"/api/bot/outbox/{jobs[0]['job']['id']}/ack", json={"message_id": 8001}, headers=BOT)
    # Acks are idempotent; a reconnecting bot may send one twice.
    assert bot.post(f"/api/bot/outbox/{jobs[0]['job']['id']}/ack", json={"message_id": 8001}, headers=BOT).is_success
    assert bot.get("/api/bot/outbox", headers=BOT).json() == []
    officer.put(f"/api/admin/posts/{post['id']}", json={"title": "Patch day", "body": "Raid moved to Thursday"})
    jobs = bot.get("/api/bot/outbox", headers=BOT).json()
    assert [(j["job"]["kind"], j["job"]["payload"]["message_id"]) for j in jobs] == [("edit_message", 8001)]
    assert jobs[0]["post"]["body"] == "Raid moved to Thursday"
    assert [a.action for a in store.audit] == ["post.create", "post.update"]


def test_posts_from_discord_are_edited_in_discord(as_: Any) -> None:
    post = as_(None).post("/api/bot/discord-messages", json=_discord_msg(ANNOUNCEMENTS, 7007, "x"), headers=BOT)
    r = as_("global officer").put(f"/api/admin/posts/{post.json()['id']}", json={"title": "y", "body": "y"})
    assert r.status_code == 409


def test_pinned_posts_come_first(as_: Any, clock: Clock) -> None:
    officer = as_("global officer")
    officer.post("/api/admin/posts", json={"title": "Rules", "body": "Be kind", "pinned": True})
    clock.now += timedelta(hours=1)
    officer.post("/api/admin/posts", json={"title": "News", "body": "Kills"})
    assert [p["title"] for p in as_("Wednesday raider").get("/api/posts").json()] == ["Rules", "News"]


@pytest.mark.security
def test_post_limits_and_unknown_fields(as_: Any) -> None:
    officer = as_("global officer")
    assert officer.post("/api/admin/posts", json={"title": "x" * 101, "body": "b"}).status_code == 422
    assert officer.post("/api/admin/posts", json={"title": "t", "body": "b" * 2001}).status_code == 422
    # Author and origin come from the session and the route, never from the body.
    r = officer.post("/api/admin/posts", json={"title": "t", "body": "b", "author_name": "GM", "origin": "discord"})
    assert r.status_code == 422


# ---------------------------------------------------- applications, interviews


def test_application_to_interview_room(as_: Any, store: CommunityStore) -> None:
    applicant, officer, bot = as_("applicant"), as_("Wednesday officer"), as_(None)
    app = applicant.post("/api/applications", json=APPLICATION)
    assert app.status_code == 201, app.text
    app_id = app.json()["id"]
    assert applicant.post("/api/applications", json=APPLICATION).status_code == 409  # one open application

    assert [a["id"] for a in officer.get("/api/days/wed/admin/applications").json()] == [app_id]
    assert as_("Sunday officer").get("/api/days/sun/admin/applications").json() == []
    r = as_("Sunday officer").post(f"/api/days/sun/admin/applications/{app_id}/interview-room")
    assert r.status_code == 404

    room = officer.post(f"/api/days/wed/admin/applications/{app_id}/interview-room")
    assert room.status_code == 202
    assert room.json()["status"] == "interviewing"
    assert officer.post(f"/api/days/wed/admin/applications/{app_id}/interview-room").status_code == 409

    [job] = bot.get("/api/bot/outbox", headers=BOT).json()
    assert job["job"]["kind"] == "create_interview_room"
    payload = job["job"]["payload"]
    assert payload["discord_user_id"] == 10_005
    assert payload["officer_role_ids"] == [12, 900]  # Wednesday officers and the global tier, not Sunday's
    bot.post(f"/api/bot/outbox/{job['job']['id']}/ack", json={"channel_id": 6001}, headers=BOT)
    mine = applicant.get("/api/applications/mine").json()
    assert mine[0]["interview_channel_id"] == 6001

    officer.post(f"/api/days/wed/admin/applications/{app_id}/transition", json={"to": "trial_offered"})
    done = officer.post(
        f"/api/days/wed/admin/applications/{app_id}/transition", json={"to": "accepted", "note": "Welcome!"}
    )
    assert [e["to_status"] for e in done.json()["events"]] == ["applied", "interviewing", "trial_offered", "accepted"]
    [lock] = bot.get("/api/bot/outbox", headers=BOT).json()
    assert lock["job"]["kind"] == "lock_interview_room"
    assert lock["job"]["payload"]["channel_id"] == 6001
    assert [(a.action, a.raid_day) for a in store.audit] == [
        ("application.interview_room", "wed"),
        ("application.trial_offered", "wed"),
        ("application.accepted", "wed"),
    ]


def test_illegal_transitions_are_refused(as_: Any) -> None:
    app_id = as_("applicant").post("/api/applications", json=APPLICATION).json()["id"]
    officer = as_("global officer")
    r = officer.post(f"/api/admin/applications/{app_id}/transition", json={"to": "accepted"})
    assert r.status_code == 409
    assert officer.post(f"/api/admin/applications/{app_id}/transition", json={"to": "withdrawn"}).status_code == 403
    officer.post(f"/api/admin/applications/{app_id}/transition", json={"to": "declined", "note": "Full on healers"})
    assert officer.post(f"/api/admin/applications/{app_id}/transition", json={"to": "interviewing"}).status_code == 409


def test_reapply_after_cooldown(as_: Any, clock: Clock) -> None:
    applicant = as_("applicant")
    app_id = applicant.post("/api/applications", json=APPLICATION).json()["id"]
    as_("global officer").post(f"/api/admin/applications/{app_id}/transition", json={"to": "declined"})
    clock.now += timedelta(days=29)
    assert applicant.post("/api/applications", json=APPLICATION).status_code == 409
    clock.now += timedelta(days=2)
    assert applicant.post("/api/applications", json=APPLICATION).status_code == 201


def test_applicant_withdraws_only_their_own(as_: Any) -> None:
    app_id = as_("applicant").post("/api/applications", json=APPLICATION).json()["id"]
    assert as_("Wednesday raider").post(f"/api/applications/{app_id}/withdraw").status_code == 404
    assert as_("applicant").post(f"/api/applications/{app_id}/withdraw").json()["status"] == "withdrawn"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("character_name", "Moss beard"),
        ("character_name", "M0ssbeard"),
        ("character_name", "<script>"),
        ("character_name", "A"),
        ("character_name", "Averyveryverylongname"),
        ("raid_days", ["fri"]),
        ("raid_days", ["WED"]),
        ("logs_url", "http://fresh.warcraftlogs.com/character/eu/x"),
        ("logs_url", "https://warcraftlogs.com.evil.example/x"),
        ("logs_url", "https://evil.example/?https://warcraftlogs.com"),
        ("logs_url", "https://user@warcraftlogs.com/x"),
        ("logs_url", "javascript:alert(1)"),
        ("experience", "x" * 1001),
        ("role", "Bard"),
    ],
)
@pytest.mark.security
def test_bad_applications_are_rejected(as_: Any, field: str, value: Any) -> None:
    r = as_("applicant").post("/api/applications", json={**APPLICATION, field: value})
    assert r.status_code == 422
    assert str(value) not in r.text or len(str(value)) < 4


def test_accented_character_names_are_fine(as_: Any) -> None:
    assert (
        as_("applicant").post("/api/applications", json={**APPLICATION, "character_name": "Fröggë"}).status_code == 201
    )


def test_applying_for_any_day_reaches_every_days_officers(as_: Any) -> None:
    as_("applicant").post("/api/applications", json={**APPLICATION, "raid_days": []})
    assert len(as_("Wednesday officer").get("/api/days/wed/admin/applications").json()) == 1
    assert len(as_("Sunday officer").get("/api/days/sun/admin/applications").json()) == 1


# --------------------------------------------------------- highlights, spotlights


def test_highlight_review_flow(as_: Any) -> None:
    raider, officer = as_("Wednesday raider"), as_("global officer")
    r = raider.post("/api/highlights", json={"title": "Vashj one-shot", "url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 201
    assert r.json()["provider"] == "youtube"
    assert r.json()["clip_id"] == "dQw4w9WgXcQ"
    assert as_(None).get("/api/public/story").json()["highlights"] == []
    assert [h["title"] for h in officer.get("/api/admin/highlights").json()] == ["Vashj one-shot"]
    officer.post(f"/api/admin/highlights/{r.json()['id']}/review", json={"action": "publish_public"})
    assert [h["title"] for h in as_(None).get("/api/public/story").json()["highlights"]] == ["Vashj one-shot"]


def test_guild_only_highlight_stays_inside(as_: Any) -> None:
    hl = as_("Wednesday raider").post(
        "/api/highlights", json={"title": "Wipe compilation", "url": "https://clips.twitch.tv/FunnyWipeClip"}
    )
    as_("global officer").post(f"/api/admin/highlights/{hl.json()['id']}/review", json={"action": "publish_guild"})
    assert as_(None).get("/api/public/story").json()["highlights"] == []
    assert len(as_("Sunday trial").get("/api/highlights").json()) == 1


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://evil.example/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "http://youtu.be/dQw4w9WgXcQ",
        'https://youtu.be/"><script>',
    ],
)
def test_highlight_urls_outside_the_allowlist_are_refused(as_: Any, url: str) -> None:
    r = as_("Wednesday raider").post("/api/highlights", json={"title": "clip", "url": url})
    assert r.status_code == 422


def test_trials_cannot_submit_highlights(as_: Any) -> None:
    r = as_("Sunday trial").post("/api/highlights", json={"title": "x", "url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 403


def test_highlight_queue_is_capped_per_member(as_: Any) -> None:
    raider = as_("Wednesday raider")
    for _ in range(5):
        raider.post("/api/highlights", json={"title": "x", "url": "https://youtu.be/dQw4w9WgXcQ"})
    r = raider.post("/api/highlights", json={"title": "x", "url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 409


SPOTLIGHT = {
    "member_id": 4,
    "character_name": "Hopscotch",
    "class_name": "Rogue",
    "headline": "Kick machine",
    "body": "Fourteen interrupts on Vashj week.",
}


def test_spotlight_needs_consent(as_: Any) -> None:
    officer, subject = as_("global officer"), as_("Wednesday raider")
    sp = officer.post("/api/admin/spotlights", json=SPOTLIGHT).json()
    assert officer.post(f"/api/admin/spotlights/{sp['id']}/publish").status_code == 409
    assert [s["headline"] for s in subject.get("/api/me/spotlights").json()] == ["Kick machine"]
    assert as_("Sunday trial").post(f"/api/me/spotlights/{sp['id']}/consent", json={"grant": True}).status_code == 404
    subject.post(f"/api/me/spotlights/{sp['id']}/consent", json={"grant": True})
    assert officer.post(f"/api/admin/spotlights/{sp['id']}/publish").json()["status"] == "published"
    assert [s["headline"] for s in as_(None).get("/api/public/story").json()["spotlights"]] == ["Kick machine"]
    # Changing their mind takes it down at once.
    assert subject.post(f"/api/me/spotlights/{sp['id']}/consent", json={"grant": False}).json()["status"] == "retired"
    assert as_(None).get("/api/public/story").json()["spotlights"] == []


def test_spotlight_subject_must_be_a_hub_member(as_: Any) -> None:
    assert (
        as_("global officer").post("/api/admin/spotlights", json={**SPOTLIGHT, "member_id": 424242}).status_code == 422
    )


# ------------------------------------------------------------ raid leader desk


def test_desk_counts_only_the_officers_days(as_: Any) -> None:
    as_("applicant").post("/api/applications", json={**APPLICATION, "raid_days": ["sun"]})
    as_(None).post("/api/bot/discord-messages", json=_discord_msg(WED_CHAT, 7100, "wed thing"), headers=BOT)
    wed = as_("Wednesday officer").get("/api/desk").json()
    assert wed == {
        "applications_waiting": 0,
        "posts_to_curate": 1,
        "highlights_to_review": 0,
        "spotlights_awaiting_consent": 0,
    }
    assert as_("Sunday officer").get("/api/desk").json()["applications_waiting"] == 1
    assert as_("global officer").get("/api/desk").json()["applications_waiting"] == 1
    assert as_("Wednesday raider").get("/api/desk").status_code == 403


def test_recruitment_needs_are_global_only(as_: Any) -> None:
    needs = [{"class_name": "Druid", "spec": "Feral", "role": "Tank", "priority": "medium", "raid_days": ["sun"]}]
    assert as_("Sunday officer").put("/api/admin/recruitment/needs", json=needs).status_code == 403
    assert as_("global officer").put("/api/admin/recruitment/needs", json=needs).status_code == 200
    assert as_(None).get("/api/public/recruitment").json()[0]["spec"] == "Feral"
    bad = [{**needs[0], "raid_days": ["fri"]}]
    assert as_("global officer").put("/api/admin/recruitment/needs", json=bad).status_code == 422
