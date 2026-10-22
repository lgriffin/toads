"""Phase 2.2 identity and RBAC: REQ-HUB-AUTH-*, REQ-HUB-RBAC-*, REQ-HUB-CLAIM-*, REQ-HUB-PRIV-*, REQ-HUB-DAY-01x/02x,
and member settings: REQ-HUB-PRIV-005 (chosen names) and REQ-HUB-KEY-* (members' own Warcraft Logs keys).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import secrets
import sys
import uuid
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest
import structlog
from hub_db import AuditEntry, Base, CredentialCipher, Member, WclCredential
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenario, then, when
from sqlalchemy import func, select
from structlog.testing import capture_logs
from toads_api.discord_api import MismatchedDiscordApplicationError
from toads_api.rbac import HubRole, UnknownDiscordRoleError
from toads_api.rbac.deps import route_rules
from toads_api.rbac.permissions import ROLE_PERMISSIONS, Permission
from toads_api.sessions import SESSION_COOKIE
from toads_worker.settings import Settings as WorkerSettings
from toads_worker.wcl_keys import MemberKeys, client_for
from wcl_core.common.errors import AuthenticationError

from conftest import CREDENTIALS_KEY, RAID_DAYS, Hub, make_settings

FEATURES = Path(__file__).resolve().parents[1] / "features"
ROOT = Path(__file__).resolve().parents[2]


def _title(feature: str, req_id: str) -> str:
    for line in (FEATURES / feature).read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario(?: Outline)?: ({req_id} .*)$", line)
        if m:
            return m.group(1)
    raise LookupError(req_id)


def _bind(feature: str, number: int) -> Any:
    """Bind the scenario REQ-<EPIC>-<nnn> from e.g. hub_auth.feature (the id is built, not written out)."""
    req_id = f"REQ-{feature.removesuffix('.feature').upper().replace('_', '-')}-{number:03d}"
    return scenario(str(FEATURES / feature), _title(feature, req_id))


@_bind("hub_auth.feature", 1)
def test_auth_001() -> None:
    pass


@_bind("hub_auth.feature", 2)
def test_auth_002() -> None:
    pass


@_bind("hub_auth.feature", 3)
def test_auth_003() -> None:
    pass


@_bind("hub_rbac.feature", 1)
def test_rbac_001() -> None:
    pass


@_bind("hub_rbac.feature", 2)
def test_rbac_002() -> None:
    pass


@_bind("hub_rbac.feature", 5)
def test_rbac_005() -> None:
    pass


@_bind("hub_rbac.feature", 6)
def test_rbac_006() -> None:
    pass


@_bind("hub_claim.feature", 1)
def test_claim_001() -> None:
    pass


@_bind("hub_claim.feature", 3)
def test_claim_003() -> None:
    pass


@_bind("hub_claim.feature", 4)
def test_claim_004() -> None:
    pass


@_bind("hub_claim.feature", 5)
def test_claim_005() -> None:
    pass


@_bind("hub_priv.feature", 3)
def test_priv_003() -> None:
    pass


@_bind("hub_day.feature", 4)
def test_day_004() -> None:
    pass


@_bind("hub_priv.feature", 4)
def test_priv_004() -> None:
    pass


@_bind("hub_priv.feature", 5)
def test_priv_005() -> None:
    pass


@_bind("hub_key.feature", 1)
def test_key_001() -> None:
    pass


@_bind("hub_key.feature", 2)
def test_key_002() -> None:
    pass


@_bind("hub_key.feature", 3)
def test_key_003() -> None:
    pass


@_bind("hub_day.feature", 10)
def test_day_010() -> None:
    pass


@_bind("hub_day.feature", 11)
def test_day_011() -> None:
    pass


@_bind("hub_day.feature", 21)
def test_day_021() -> None:
    pass


@_bind("hub_day.feature", 22)
def test_day_022() -> None:
    pass


@_bind("hub_day.feature", 23)
def test_day_023() -> None:
    pass


@_bind("hub_day.feature", 24)
def test_day_024() -> None:
    pass


@_bind("hub_day.feature", 25)
def test_day_025() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _audit(hub: Hub) -> list[tuple[str, str | None]]:
    with hub.db() as db:
        return [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]


def _character(hub: Hub, name: str) -> int:
    return next(cid for cid, n in hub.characters.names.items() if n == name)


# --- people ------------------------------------------------------------------------------------------


@given(parsers.parse('a Wednesday raider signed in with server nickname "{nick}"'))
def raider(hub: Hub, ctx: dict[str, Any], nick: str) -> None:
    ctx["user"] = hub.user(("wed", "raider"), nick=nick)
    ctx["sid"] = hub.login(ctx["user"])


DAY_IDS = {d.name: d.id for d in RAID_DAYS.raid_days}


@given(parsers.re(r"a (?P<day>Wednesday|Thursday|Sunday) officer signed in$"))
def day_officer(hub: Hub, ctx: dict[str, Any], day: str) -> None:
    ctx["officer_user"] = hub.user((DAY_IDS[day], "officer"))
    ctx["officer"] = hub.login(ctx["officer_user"])


@given("a Discord user who is not in the Toads server")
def stranger(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["user"] = hub.user(in_guild=False)


@given("a Sunday raider has a pending claim")
def sunday_claim(hub: Hub, ctx: dict[str, Any]) -> None:
    sid = hub.login(hub.user(("sun", "raider"), nick="Someone"))
    ctx["claim"] = hub.post("/api/claims", sid, {"character_id": _character(hub, "Croak")}).json()
    ctx["claimant"] = sid
    assert ctx["claim"]["raid_day_id"] == "sun"


# --- auth --------------------------------------------------------------------------------------------


@given("the hub API")
def the_api(hub: Hub) -> None:
    pass


@then("signing in redirects to Discord with a PKCE challenge")
def redirects_with_pkce(hub: Hub) -> None:
    location = hub.start_login().headers["location"]
    assert location.startswith(hub.services.settings.discord_authorize_url)
    assert "code_challenge_method=S256" in location


@then("no route or table holds a hub password")
def no_passwords(hub: Hub) -> None:
    rules, public = route_rules(hub.app)
    paths = [r.path for r in rules] + public
    assert not [p for p in paths if re.search("password|register|signup", p, re.I)]
    # Officer tokens (docs/admin.md) are kept as hashes, but they grant bank permissions once and never sign anyone in.
    # Logs pages (docs/logs.md) keep the worker's content hashes of each raid's analysis, which are not secrets at all.
    not_sign_in = {("bank_grant_tokens", "token_hash"), ("log_raids", "page_hash"), ("log_raids", "want_hash")}
    columns = [(t.name, c.name) for t in Base.metadata.tables.values() for c in t.columns]
    assert not [c for c in columns if ("password" in c[1] or "hash" in c[1]) and c not in not_sign_in]


@when("they complete Discord sign-in")
def complete_sign_in(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.callback(hub.authorize(hub.start_login(), ctx["user"]))


@then("the hub sends them to the members only page")
def members_only(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 303
    assert ctx["response"].headers["location"].endswith("/members-only")


@then("no session is created")
def no_session(hub: Hub, ctx: dict[str, Any]) -> None:
    assert SESSION_COOKIE not in ctx["response"].cookies
    keys = hub.client.portal.call(hub.redis.keys, "toads:session:*")
    assert keys == []
    with hub.db() as db:
        assert db.scalar(select(func.count()).select_from(Member)) == 0


# --- rbac --------------------------------------------------------------------------------------------


@then('their session reports officer standing for raid day "wed" only')
def officer_on_wed_only(hub: Hub, ctx: dict[str, Any]) -> None:
    info = hub.get("/api/session", ctx["officer"]).json()
    assert info["day_roles"] == {"wed": "officer"}
    assert info["global_officer"] is False


@then("no route or table besides officer grants assigns hub roles")
def no_role_assignment(hub: Hub) -> None:
    rules, _ = route_rules(hub.app)
    # Role badges (docs/role-badges.md) read Discord roles to hand out badge art; they grant no permission.
    badge_desk = "/api/admin/role-badges"
    assert not [r for r in rules if r.method != "GET" and "role" in r.path and not r.path.startswith(badge_desk)]
    assert not [c.name for c in Member.__table__.columns if "role" in c.name]
    # Officer grants (REQ-HUB-RBAC-005) are the one hub-side assignment, and only super admins reach them.
    officer_desk = [r for r in rules if r.path.startswith("/api/admin/officer-grants")]
    assert officer_desk and {r.permission for r in officer_desk} == {Permission.MANAGE_OFFICER_GRANTS}


# --- officer grants (REQ-HUB-RBAC-005) -----------------------------------------------------------------


@given("a super admin and a Wednesday raider signed in")
def admin_and_raider(hub: Hub, ctx: dict[str, Any]) -> None:
    admin = hub.user()
    hub.services.settings = make_settings(super_admin_ids=str(admin.user_id))
    ctx["admin"] = hub.login(admin)
    ctx["raider_user"] = hub.user(("wed", "raider"))
    ctx["raider"] = hub.login(ctx["raider_user"])


def _officer_grant(hub: Hub, ctx: dict[str, Any], sid: str, day: str | None) -> httpx.Response:
    body = {"discord_user_id": str(ctx["raider_user"].user_id), "raid_day": day}
    return hub.post("/api/admin/officer-grants", sid, body)


@when(parsers.parse('the super admin grants the raider officer powers for raid day "{day}"'))
def grant_day_officer(hub: Hub, ctx: dict[str, Any], day: str) -> None:
    assert _officer_grant(hub, ctx, ctx["admin"], day).status_code == 201


@when("the super admin grants the raider global officer powers")
def grant_global_officer(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _officer_grant(hub, ctx, ctx["admin"], None).status_code == 201


@when("the super admin revokes the raider's officer grants")
def revoke_officer_grants(hub: Hub, ctx: dict[str, Any]) -> None:
    for g in hub.get("/api/admin/officer-grants", ctx["admin"]).json()["grants"]:
        assert hub.delete(f"/api/admin/officer-grants/{g['id']}", ctx["admin"]).status_code == 204


@then(
    parsers.parse('the raider\'s session reports officer standing for raid day "{day}" and raider standing for "{own}"')
)
def granted_day_standing(hub: Hub, ctx: dict[str, Any], day: str, own: str) -> None:
    info = hub.get("/api/session", ctx["raider"]).json()
    assert info["day_roles"] == {own: "raider", day: "officer"}
    assert (info["officer_days"], info["global_officer"]) == ([day], False)


@then("the raider's session reports a global officer who is not a super admin")
def granted_global_standing(hub: Hub, ctx: dict[str, Any]) -> None:
    info = hub.get("/api/session", ctx["raider"]).json()
    assert (info["global_officer"], info["super_admin"], info["break_glass"]) == (True, False, False)


@then("the raider may not grant officer powers")
def raider_cannot_grant(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _officer_grant(hub, ctx, ctx["raider"], "wed").status_code == 403


@then("the raider's session reports no officer standing")
def no_officer_standing(hub: Hub, ctx: dict[str, Any]) -> None:
    info = hub.get("/api/session", ctx["raider"]).json()
    assert (info["day_roles"], info["officer_days"], info["global_officer"]) == ({"wed": "raider"}, [], False)


@then("the audit log records each officer grant and revoke")
def officer_grants_audited(hub: Hub) -> None:
    with hub.db() as db:
        rows = [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert [r for r in rows if r[0].startswith("officer.")] == [
        ("officer.grant", "sun"),
        ("officer.grant", None),
        ("officer.revoke", "sun"),
        ("officer.revoke", None),
    ]


# --- view as (REQ-HUB-RBAC-006) ------------------------------------------------------------------------


@given("a super admin signed in")
def super_admin_signed_in(hub: Hub, ctx: dict[str, Any]) -> None:
    admin = hub.user(("wed", "officer"))
    hub.services.settings = make_settings(super_admin_ids=str(admin.user_id))
    ctx["admin"] = hub.login(admin)


@when(parsers.parse('the super admin views the hub as the "{day}" {role}'))
def view_as(hub: Hub, ctx: dict[str, Any], day: str, role: str) -> None:
    r = hub.put(f"/api/admin/view-as/{role}/{day}", ctx["admin"])
    assert r.status_code == 200, r.text
    assert r.json() == {"role": role, "raid_day": day, "name": RAID_DAYS.day(day).name}  # type: ignore[union-attr]


@then(
    parsers.parse(
        'their session reports viewing as the "{day}" raider with raider standing for "{also}" only and no super admin'
    )
)
def viewing_as_raider(hub: Hub, ctx: dict[str, Any], day: str, also: str) -> None:
    s = hub.get("/api/session", ctx["admin"]).json()
    assert s["view_as"] == {"role": "raider", "raid_day": day, "name": "Sunday"}
    assert (s["day_roles"], s["officer_days"]) == ({also: "raider"}, [])
    assert not (s["super_admin"] or s["global_officer"])


@then("they may not reach the officers' or super admins' routes")
def viewer_kept_out(hub: Hub, ctx: dict[str, Any]) -> None:
    for path in ("/api/days/sun/claims", "/api/days/wed/claims", "/api/admin/officer-grants"):
        assert hub.get(path, ctx["admin"]).status_code == 403, path


@then("every change they try is refused as read only")
def viewer_read_only(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.post("/api/days/sun/absences", ctx["admin"], {"starts_on": "2026-11-01", "ends_on": "2026-11-01"})
    assert r.status_code == 403
    assert "read only" in r.json()["detail"]


@then(parsers.parse('they may reach the officers\' routes for "{day}" but not for "{other}"'))
def viewer_as_officer(hub: Hub, ctx: dict[str, Any], day: str, other: str) -> None:
    assert hub.get(f"/api/days/{day}/claims", ctx["admin"]).status_code == 200
    assert hub.get(f"/api/days/{other}/claims", ctx["admin"]).status_code == 403
    assert hub.get("/api/session", ctx["admin"]).json()["officer_days"] == [day]


@when("the super admin goes back")
def go_back(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.delete("/api/admin/view-as", ctx["admin"]).status_code == 204


@then("their session reports a super admin again")
def super_admin_again(hub: Hub, ctx: dict[str, Any]) -> None:
    s = hub.get("/api/session", ctx["admin"]).json()
    assert s["super_admin"] and s["view_as"] is None
    assert hub.get("/api/admin/officer-grants", ctx["admin"]).status_code == 200


@then("the audit log records each view as start and end")
def view_as_audited(hub: Hub) -> None:
    with hub.db() as db:
        rows = [(a.action, a.target, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert [r for r in rows if r[0].startswith("view_as.")] == [
        ("view_as.start", "raider", "sun"),
        ("view_as.start", "officer", "sun"),
        ("view_as.end", "officer", "sun"),
    ]


@when("they gain the Sunday raider role in Discord")
def gain_role(ctx: dict[str, Any]) -> None:
    ctx["officer_user"].roles.add(21)


@when("their Wednesday officer role is removed in Discord")
def lose_role(ctx: dict[str, Any]) -> None:
    ctx["officer_user"].roles.discard(12)


@when("15 minutes pass")
def fifteen_minutes(hub: Hub) -> None:
    hub.pass_time(15 * 60)


@then(parsers.parse('their session reports {role} standing for raid day "{day}"'))
def reports_standing(hub: Hub, ctx: dict[str, Any], role: str, day: str) -> None:
    assert hub.get("/api/session", ctx["officer"]).json()["day_roles"][day] == role


@then("their next request is refused and the session is gone")
def session_gone(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/session", ctx["officer"]).status_code == 401
    assert hub.client.portal.call(hub.redis.keys, "toads:session:*") == []


# --- claims ------------------------------------------------------------------------------------------


@given(parsers.parse('they claim the character "{name}"'))
@when(parsers.parse('they claim the character "{name}"'))
def claim(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    r = hub.post("/api/claims", ctx["sid"], {"character_id": _character(hub, name)})
    assert r.status_code == 201, r.text
    ctx["claim"] = r.json()


@when(parsers.parse('they search for characters named "{query}"'))
def search(hub: Hub, ctx: dict[str, Any], query: str) -> None:
    r = hub.get(f"/api/characters?q={query}", ctx["sid"])
    assert r.status_code == 200, r.text
    ctx["found"] = [c["name"] for c in r.json()]


@then(parsers.parse('they are offered "{first}" and "{second}"'))
def offered(ctx: dict[str, Any], first: str, second: str) -> None:
    assert ctx["found"] == [first, second]


@then("the claim is approved")
def claim_approved(ctx: dict[str, Any]) -> None:
    assert ctx["claim"]["status"] == "approved"


@then("the claim is pending")
def claim_pending(ctx: dict[str, Any]) -> None:
    assert ctx["claim"]["status"] == "pending"


def _outbox(hub: Hub) -> list[bytes]:
    return list(hub.client.portal.call(hub.redis.lrange, "toads:outbox:officers", 0, -1))


@then("#officers only gets an FYI they can reassign from")
def fyi_only(hub: Hub, ctx: dict[str, Any]) -> None:
    [event] = _outbox(hub)
    assert b'"kind": "claim_auto_approved"' in event
    assert f'"claim_id": {ctx["claim"]["id"]}'.encode() in event


@then("#officers is notified of the claim")
def notified(hub: Hub, ctx: dict[str, Any]) -> None:
    [event] = _outbox(hub)
    assert f'"claim_id": {ctx["claim"]["id"]}'.encode() in event


@when(parsers.parse("a Wednesday officer decides to {action} the claim"))
def officer_decides(hub: Hub, ctx: dict[str, Any], action: str) -> None:
    officer = hub.login(hub.user(("wed", "officer")))
    other = hub.login(hub.user(("wed", "raider")))
    ctx["other_member"] = hub.get("/api/session", other).json()["member_id"]
    body = {"approve": None, "reject": {"reason": "Belongs to Ribbit"}, "reassign": {"member_id": ctx["other_member"]}}
    r = hub.post(f"/api/days/wed/claims/{ctx['claim']['id']}/{action}", officer, body[action])
    assert r.status_code == 200, r.text
    ctx["decided"] = r.json()


@then(parsers.parse("the claim ends {outcome}"))
def claim_ends(ctx: dict[str, Any], outcome: str) -> None:
    decided = ctx["decided"]
    if outcome == "approved":
        assert decided["status"] == "approved"
    elif outcome == "rejected with the reason":
        assert (decided["status"], decided["reason"]) == ("rejected", "Belongs to Ribbit")
    else:
        assert (decided["status"], decided["member_id"]) == ("approved", ctx["other_member"])


@then(parsers.parse('the decision is in the audit log for raid day "{day}"'))
def decision_audited(hub: Hub, day: str) -> None:
    action, raid_day = _audit(hub)[-1]
    assert action.startswith("claim.")
    assert raid_day == day


@then("the Wednesday officers' claims panel lists the claim with the claimant's name")
def wed_panel_lists(hub: Hub, ctx: dict[str, Any]) -> None:
    officer = hub.login(hub.user(("wed", "officer")))
    queued = [(c["id"], c["member_name"]) for c in hub.get("/api/days/wed/claims", officer).json()]
    assert queued == [(ctx["claim"]["id"], "Hops")]


@then("the Sunday officers' claims panel does not list it")
def sun_panel_empty(hub: Hub) -> None:
    assert hub.get("/api/days/sun/claims", hub.login(hub.user(("sun", "officer")))).json() == []


@then("the global officers' no-night list does not list it")
def unplaced_empty(hub: Hub) -> None:
    assert hub.get("/api/admin/claims", hub.login(hub.user(("global", "officer")))).json() == []


@given(parsers.parse('they hold an officer-approved claim on "{name}"'))
def approved_claim(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    r = hub.post("/api/claims", ctx["sid"], {"character_id": _character(hub, name)})
    officer = hub.login(hub.user(("wed", "officer")))
    assert hub.post(f"/api/days/wed/claims/{r.json()['id']}/approve", officer).status_code == 200


@when(parsers.parse('they ask to make "{name}" their main'))
def ask_main(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    r = hub.post("/api/me/main", ctx["sid"], {"character_id": _character(hub, name)})
    assert r.status_code == 201, r.text
    ctx["swap"] = r.json()


@then(parsers.parse('their main is still "{name}"'))
@then(parsers.parse('their main is "{name}"'))
def main_is(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    assert hub.get("/api/me/main", ctx["sid"]).json()["main"]["character_name"] == name


@then(parsers.parse('the Wednesday officers\' claims panel lists the main swap to "{name}"'))
def wed_lists_swap(hub: Hub, name: str) -> None:
    officer = hub.login(hub.user(("wed", "officer")))
    assert [s["character_name"] for s in hub.get("/api/days/wed/main-swaps", officer).json()] == [name]


@then("the Sunday officers' claims panel lists no main swap")
def sun_lists_no_swap(hub: Hub) -> None:
    assert hub.get("/api/days/sun/main-swaps", hub.login(hub.user(("sun", "officer")))).json() == []


@when("a Wednesday officer approves the main swap")
def approve_swap(hub: Hub, ctx: dict[str, Any]) -> None:
    officer = hub.login(hub.user(("wed", "officer")))
    r = hub.post(f"/api/days/wed/main-swaps/{ctx['swap']['id']}/approve", officer)
    assert r.status_code == 200, r.text


@when("they unclaim it")
def unclaim(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.delete(f"/api/claims/{ctx['claim']['id']}", ctx["sid"]).status_code == 204


@then("they no longer hold the claim")
def no_claim(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/claims", ctx["sid"]).json() == []


@then("the character can be claimed again")
def claimable(hub: Hub, ctx: dict[str, Any]) -> None:
    other = hub.login(hub.user(("sun", "raider")))
    assert hub.post("/api/claims", other, {"character_id": ctx["claim"]["character_id"]}).status_code == 201


# --- session days and members directory ------------------------------------------------------------


@given("a member signed in with the Wednesday raider and Sunday officer roles")
def raider_and_officer(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["sid"] = hub.login(hub.user(("wed", "raider"), ("sun", "officer")))


@given("a global officer signed in")
def global_officer(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["sid"] = hub.login(hub.user(("global", "officer")))


def _days(text: str) -> list[str]:
    return [d.strip() for d in text.split(",") if d.strip()]


@then(parsers.re(r'their session lists raid days "(?P<raid>[^"]*)" and officer days "(?P<officer>[^"]*)"'))
def session_days(hub: Hub, ctx: dict[str, Any], raid: str, officer: str) -> None:
    info = hub.get("/api/session", ctx["sid"]).json()
    assert (info["raid_days"], info["officer_days"]) == (_days(raid), _days(officer))


@then("they are not a global officer")
def not_global(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/session", ctx["sid"]).json()["global_officer"] is False


@then("they are a global officer")
def is_global(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/session", ctx["sid"]).json()["global_officer"] is True


@when("the raider lists the members")
def raider_lists(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["members"] = hub.get("/api/members", ctx["sid"]).json()


@when("the officer lists the members")
def officer_lists(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["members"] = hub.get("/api/members", ctx["officer"]).json()


@then(parsers.parse('they see "{name}" and no Discord user ids'))
def sees_names_only(ctx: dict[str, Any], name: str) -> None:
    assert name in [m["display_name"] for m in ctx["members"]]
    assert all(m["discord_user_id"] is None for m in ctx["members"])


@then("they see every member's Discord user id")
def sees_ids(ctx: dict[str, Any]) -> None:
    assert len(ctx["members"]) == 2
    assert {m["discord_user_id"] for m in ctx["members"]} == {
        str(ctx["user"].user_id),
        str(ctx["officer_user"].user_id),
    }


@then("signed-out visitors cannot list the members")
def anonymous_denied(hub: Hub) -> None:
    assert hub.get("/api/members", None).status_code == 401


# --- raid-day scope ----------------------------------------------------------------------------------


@then(parsers.parse("they can open the {day} claims queue"))
def open_queue(hub: Hub, ctx: dict[str, Any], day: str) -> None:
    assert hub.get(f"/api/days/{DAY_IDS[day]}/claims", ctx["officer"]).status_code == 200


@then("they can trigger a Wednesday sync")
def wed_sync(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.post("/api/days/wed/admin/sync", ctx["officer"]).status_code == 202


@then(parsers.parse("every {day} officer view answers them 403"))
def other_day_views_denied(hub: Hub, ctx: dict[str, Any], day: str) -> None:
    rules, _ = route_rules(hub.app)
    # Officer views only: scoped routes a plain member may also open (a day's raid sheets) stay open.
    scoped = [r for r in rules if r.scoped and r.permission not in ROLE_PERMISSIONS[HubRole.MEMBER]]
    assert scoped
    for rule in scoped:
        path = re.sub(r"\{[a-z_]+\}", "1", rule.path.replace("{day}", DAY_IDS[day]))
        r = hub.client.request(rule.method, path, headers=hub.as_(ctx["officer"]), json={})
        assert r.status_code == 403, (rule, r.status_code)


@when("the Wednesday officer requests the Sunday claims queue")
def request_sunday_queue(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.get("/api/days/sun/claims", ctx["officer"])


@when("the Wednesday officer approves the Sunday claim through the Wednesday path")
def approve_via_wed(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.post(f"/api/days/wed/claims/{ctx['claim']['id']}/approve", ctx["officer"])


@then("the hub answers 403")
def answers_403(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 403


@then(parsers.parse('the attempt is in the audit log for raid day "{day}"'))
def attempt_audited(hub: Hub, day: str) -> None:
    assert _audit(hub)[-1] == ("rbac.denied", day)


@then("the claim is still pending")
def still_pending(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/claims", ctx["claimant"]).json()[0]["status"] == "pending"


@when(parsers.parse('they trigger a Sunday sync with "{day}" in the query and the body'))
def sync_with_smuggled_day(hub: Hub, ctx: dict[str, Any], day: str) -> None:
    ctx["response"] = hub.client.post(
        f"/api/days/sun/admin/sync?day={day}", headers=hub.as_(ctx["officer"]), json={"day": day}
    )


@then("every officer route is scoped by a raid day in its path, or is a global-officer route")
def officer_routes_scoped(hub: Hub) -> None:
    matrix = _matrix_module()
    rules, _ = route_rules(hub.app)
    officer = [r for r in rules if r.permission in matrix.OFFICER_ONLY]
    assert officer
    assert all(
        (r.scoped and "{day}" in r.path) or (not r.scoped and r.path.startswith(matrix.GLOBAL_ADMIN_PREFIX))
        for r in officer
    )


@then("the RBAC matrix has a sibling-day denial case for every officer route")
def matrix_has_sibling_cases(hub: Hub) -> None:
    matrix = _matrix_module()
    rules, _ = route_rules(hub.app)
    for rule in (r for r in rules if r.permission in matrix.OFFICER_ONLY and r.scoped):
        sibling = [c for c in matrix.matrix() if c.rule == rule and c.tier == "officer" and c.sibling]
        assert sibling
        assert not any(matrix.expected_allowed(c.tier, c.own_day, rule.permission, c.target_day) for c in sibling)


def _matrix_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "rbac_matrix", ROOT / "services" / "api" / "tests" / "test_rbac_matrix.py"
    )
    assert spec and spec.loader
    module = sys.modules.get(spec.name) or importlib.util.module_from_spec(spec)
    if spec.name not in sys.modules:
        sys.modules[spec.name] = module  # dataclasses need their module registered
        spec.loader.exec_module(module)
    return module


@given(parsers.parse("a raid-day config naming Discord role {role:d} for Sunday officers"))
def config_with_role(ctx: dict[str, Any], role: int) -> None:
    cfg = RAID_DAYS.model_copy(deep=True)
    cfg.raid_days[-1].officer_roles.append(role)
    ctx["cfg"] = cfg


@given(parsers.parse("the Discord server has no role {role:d}"))
def server_lacks_role(ctx: dict[str, Any], role: int) -> None:
    ctx["hub"] = Hub(raid_days=ctx["cfg"])
    assert role not in ctx["hub"].fake.guild_roles


@given(parsers.parse("the hub's bot token belongs to Discord application {app_id:d}"))
def bot_token_application(ctx: dict[str, Any], app_id: int) -> None:
    ctx["hub"] = Hub()
    ctx["hub"].fake.bot_application_id = str(app_id)


@given("the hub's Discord client id is a different application")
def client_id_differs(ctx: dict[str, Any]) -> None:
    assert ctx["hub"].services.settings.discord_client_id != ctx["hub"].fake.bot_application_id


@given("Toad Bot has not been invited to the Discord server")
def bot_not_in_server(ctx: dict[str, Any]) -> None:
    ctx["hub"] = Hub()
    ctx["hub"].fake.bot_in_server = False


@when("the API starts")
def api_starts(ctx: dict[str, Any]) -> None:
    try:
        with capture_logs() as logs, ctx["hub"].client:
            ctx["error"] = None
            ctx["health"] = ctx["hub"].client.get("/healthz").status_code
    except (UnknownDiscordRoleError, MismatchedDiscordApplicationError) as exc:
        ctx["error"] = exc
    ctx["logs"] = logs


@then("the API is up")
def api_is_up(ctx: dict[str, Any]) -> None:
    assert ctx["error"] is None
    assert ctx["health"] == 200


@then("it warns that the server's roles were not checked, naming TOADS_DISCORD_GUILD_ID")
def warned_roles_unchecked(ctx: dict[str, Any]) -> None:
    [warning] = [e for e in ctx["logs"] if e["event"] == "discord_roles_unchecked"]
    assert warning["log_level"] == "warning"
    assert "TOADS_DISCORD_GUILD_ID" in warning["hint"]
    assert "https://discord.com/oauth2/authorize?client_id=toads-dev&" in warning["hint"]
    assert "HTTP 404" in warning["error"]


@then("it logs an error naming TOADS_DISCORD_CLIENT_ID and TOADS_DISCORD_BOT_TOKEN")
def logged_mismatched_application(ctx: dict[str, Any]) -> None:
    [error] = [e for e in ctx["logs"] if e["event"] == "discord_application_misconfigured"]
    assert error["log_level"] == "error"
    assert "TOADS_DISCORD_CLIENT_ID" in error["error"]
    assert "TOADS_DISCORD_BOT_TOKEN" in error["error"]


@then(parsers.parse('it logs an error naming raid day "{day}" and role {role:d}'))
def logged_unknown_role(ctx: dict[str, Any], day: str, role: int) -> None:
    [error] = [e for e in ctx["logs"] if e["event"] == "discord_role_missing"]
    assert error["log_level"] == "error"
    assert f"raid day '{day}'" in error["error"]
    assert str(role) in error["error"]


# --- member settings: chosen names (REQ-HUB-PRIV-005) --------------------------------------------------


@given("a Wednesday officer approves the claim")
def officer_approves(hub: Hub, ctx: dict[str, Any]) -> None:
    officer = hub.login(hub.user(("wed", "officer")))
    r = hub.post(f"/api/days/wed/claims/{ctx['claim']['id']}/approve", officer)
    assert r.status_code == 200, r.text


@when(parsers.parse('they choose "{name}" as their name'))
def choose_name(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    r = hub.client.put(
        "/api/me/name", headers=hub.as_(ctx["sid"]), json={"source": "character", "character_id": _character(hub, name)}
    )
    assert r.status_code == 200, r.text
    assert r.json()["shown_name"] == name


@then(parsers.parse('the members list and their session show "{name}"'))
def shown_everywhere(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    session = hub.get("/api/session", ctx["sid"]).json()
    assert session["display_name"] == name
    members = {m["member_id"]: m["display_name"] for m in hub.get("/api/members", ctx["sid"]).json()}
    assert members[session["member_id"]] == name
    assert hub.get("/api/me/settings", ctx["sid"]).json()["shown_name"] == name


@then("they cannot choose a character they have not claimed")
def cannot_choose_unclaimed(hub: Hub, ctx: dict[str, Any]) -> None:
    body = {"source": "character", "character_id": _character(hub, "Croak")}
    assert hub.client.put("/api/me/name", headers=hub.as_(ctx["sid"]), json=body).status_code == 422


# --- member settings: own Warcraft Logs keys (REQ-HUB-KEY-*) --------------------------------------------


class FakeTokens:
    """Stands in for wcl_core's TokenManager: records which client id asked for a token, refuses listed ones."""

    refused: ClassVar[set[str]] = set()
    used: ClassVar[list[str]] = []

    def __init__(self, client_id: str, client_secret: str | SecretStr) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        FakeTokens.used.append(client_id)

    def get_token(self) -> str:
        if self.client_id in FakeTokens.refused:
            raise AuthenticationError("Authentication failed (HTTP 401)")
        return "token"


GUILD_CLIENT_ID = "guild-client-id"


def _client_id_for(hub: Hub, member_id: int | None) -> str:
    settings = WorkerSettings(
        database_url=SecretStr("sqlite://"),
        redis_url="redis://fake",
        wcl_client_id=GUILD_CLIENT_ID,
        wcl_client_secret=SecretStr("replace-me"),
        wcl_guild_id=1,
        credentials_keys=SecretStr(CREDENTIALS_KEY),
    )
    keys = MemberKeys(hub.db, CredentialCipher([CREDENTIALS_KEY]))
    client = client_for(settings, member_id, keys=keys, tokens=FakeTokens)  # type: ignore[arg-type]
    token_manager: FakeTokens = client.token_manager
    return token_manager.client_id


@pytest.fixture(autouse=True)
def _reset_fake_tokens() -> None:
    FakeTokens.refused = set()
    FakeTokens.used = []


@when("they save their own Warcraft Logs key")
def save_key(hub: Hub, ctx: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    # Built at runtime: literal key-shaped strings trip the secret scanners.
    ctx["client_id"], ctx["client_secret"] = str(uuid.uuid4()), secrets.token_urlsafe(30)
    ctx["member_id"] = hub.get("/api/session", ctx["sid"]).json()["member_id"]
    caplog.set_level(logging.DEBUG)
    with structlog.testing.capture_logs() as logs:
        r = hub.client.put(
            "/api/me/wcl-key",
            headers=hub.as_(ctx["sid"]),
            json={"client_id": ctx["client_id"], "client_secret": ctx["client_secret"]},
        )
        ctx["member_client_id"] = _client_id_for(hub, ctx["member_id"])
    assert r.status_code == 200, r.text
    ctx["saved"] = r
    ctx["logs"] = repr(logs) + caplog.text


@when("they remove their key")
def remove_key(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.delete("/api/me/wcl-key", ctx["sid"])
    assert r.status_code == 200, r.text
    assert r.json()["wcl_key"] is None


@when("Warcraft Logs refuses that key")
def refuse_key(ctx: dict[str, Any]) -> None:
    FakeTokens.refused.add(ctx["client_id"])


@then("work done for them uses their key")
def uses_member_key(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _client_id_for(hub, ctx["member_id"]) == ctx["client_id"]
    assert hub.get("/api/me/settings", ctx["sid"]).json()["wcl_key"]["status"] == "working"


@then("work done for the guild still uses the guild key")
def guild_uses_guild_key(hub: Hub) -> None:
    assert _client_id_for(hub, None) == GUILD_CLIENT_ID


@then("work done for them uses the guild key")
def member_uses_guild_key(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _client_id_for(hub, ctx["member_id"]) == GUILD_CLIENT_ID
    assert hub.get("/api/me/settings", ctx["sid"]).json()["wcl_key_in_use"] == "guild"


@then("their settings show only the last four characters of the client id")
def settings_hide_key(hub: Hub, ctx: dict[str, Any]) -> None:
    for body in (ctx["saved"].text, hub.get("/api/me/settings", ctx["sid"]).text):
        assert ctx["client_secret"] not in body
        assert ctx["client_id"] not in body
    key = hub.get("/api/me/settings", ctx["sid"]).json()["wcl_key"]
    assert key["client_id_hint"] == ctx["client_id"][-4:]


@then("the database holds neither the client id nor the secret in plain text")
def encrypted_at_rest(hub: Hub, ctx: dict[str, Any]) -> None:
    with hub.db() as db:
        row = db.get(WclCredential, ctx["member_id"])
        assert row is not None
        stored = " ".join(str(getattr(row, c.name)) for c in WclCredential.__table__.columns)
    assert ctx["client_id"] not in stored
    assert ctx["client_secret"] not in stored


@then("no log line carries the client id or the secret")
def not_logged(ctx: dict[str, Any]) -> None:
    assert ctx["client_id"] not in ctx["logs"]
    assert ctx["client_secret"] not in ctx["logs"]


@then("their settings show the key as rejected")
def shows_rejected(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.get("/api/me/settings", ctx["sid"]).json()["wcl_key"]["status"] == "rejected"
