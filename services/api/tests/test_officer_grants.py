"""Officer grants (docs/admin.md "Officer grants"): the rules in OfficerGrantService, the routes, and what a grant
gives the grantee's session. A grant never makes anyone a super admin."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hub_db import AuditEntry
from sqlalchemy import select
from toads_api.discord_api import DiscordError
from toads_api.officer_grants.repository import InMemoryOfficerGrantRepository
from toads_api.officer_grants.service import NO_STANDING, OfficerGrantError, OfficerGrantService
from toads_api.rbac import HubRole, RaidDaysConfig

from conftest import Hub, make_settings

DAYS = ("wed", "thu", "sun")

# ---------------------------------------------------------------- rules


def test_standing_follows_the_grants_and_ignores_days_the_config_dropped() -> None:
    repo = InMemoryOfficerGrantRepository()
    svc = OfficerGrantService(repo, DAYS)
    assert svc.standing(41) is NO_STANDING
    svc.grant(41, "bob", "Bob", "wed", granted_by=1)
    repo.grants[99] = replace(repo.grants[1], id=99, raid_day="fri")  # a night since dropped from raid_days.yaml
    standing = svc.standing(41)
    assert (standing.days, standing.global_officer) == (frozenset({"wed"}), False)
    svc.grant(41, "bob", "Bob", None, granted_by=1)
    assert svc.standing(41).global_officer
    assert svc.standing(42) is NO_STANDING


def test_granting_twice_keeps_one_grant_and_unknown_days_and_ids_are_refused() -> None:
    svc = OfficerGrantService(InMemoryOfficerGrantRepository(), DAYS)
    first, created = svc.grant(41, "bob", "  Bob  ", "sun", granted_by=1)
    again, created_again = svc.grant(41, "bob", "Bob", "sun", granted_by=2)
    assert (created, created_again, again.id, first.display_name) == (True, False, first.id, "Bob")
    for day, user in (("fri", 41), ("wed", 0)):
        with pytest.raises(OfficerGrantError) as info:
            svc.grant(user, "bob", "Bob", day, granted_by=1)
        assert info.value.status == 422
    svc.revoke(first.id, revoked_by=1)
    with pytest.raises(OfficerGrantError) as info:
        svc.revoke(first.id, revoked_by=1)
    assert info.value.status == 404


def test_grants_layer_on_top_of_discord_roles_and_never_make_a_super_admin() -> None:
    cfg = RaidDaysConfig.model_validate(
        {"raid_days": [{"id": "wed", "name": "Wednesday", "raider_roles": [11]}, {"id": "sun", "name": "Sunday"}]}
    )
    p = cfg.principal_for(1, {11}, officer_days={"sun"})
    assert p.day_roles == {"wed": HubRole.RAIDER, "sun": HubRole.OFFICER}
    assert not p.global_officer
    p = cfg.principal_for(1, set(), granted_global_officer=True)
    assert p.global_officer and not p.super_admin


# ---------------------------------------------------------------- routes


def _super_admin(hub: Hub) -> str:
    user = hub.user()
    hub.services.settings = make_settings(super_admin_ids=str(user.user_id))
    return hub.login(user)


def _grant(hub: Hub, sid: str, user_id: int, day: str | None):  # type: ignore[no-untyped-def]
    return hub.post("/api/admin/officer-grants", sid, {"discord_user_id": str(user_id), "raid_day": day})


def test_a_day_grant_makes_an_officer_of_that_night_only_and_a_revoke_counts_at_once(hub: Hub) -> None:
    admin = _super_admin(hub)
    raider = hub.user(("wed", "raider"))
    sid = hub.login(raider)
    assert hub.get("/api/session", sid).json()["officer_days"] == []

    made = _grant(hub, admin, raider.user_id, "sun")
    assert made.status_code == 201, made.text
    assert made.json()["username"] == raider.username
    assert _grant(hub, admin, raider.user_id, "sun").status_code == 200  # already held
    info = hub.get("/api/session", sid).json()
    assert info["officer_days"] == ["sun"]
    assert info["day_roles"] == {"wed": "raider", "sun": "officer"}
    assert (info["global_officer"], info["super_admin"]) == (False, False)
    assert hub.post("/api/days/sun/admin/sync", sid, None).status_code == 202
    assert hub.post("/api/days/wed/admin/sync", sid, None).status_code == 403

    listed = hub.get("/api/admin/officer-grants", admin).json()
    assert [(g["discord_user_id"], g["raid_day"]) for g in listed["grants"]] == [(str(raider.user_id), "sun")]
    assert [d["id"] for d in listed["raid_days"]] == [d.id for d in hub.services.raid_days.raid_days]

    assert hub.delete(f"/api/admin/officer-grants/{made.json()['id']}", admin).status_code == 204
    assert hub.delete(f"/api/admin/officer-grants/{made.json()['id']}", admin).status_code == 404
    assert hub.get("/api/session", sid).json()["officer_days"] == []
    with hub.db() as db:
        actions = [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert [a for a in actions if a[0].startswith("officer.")] == [("officer.grant", "sun"), ("officer.revoke", "sun")]


def test_a_global_grant_makes_a_global_officer_but_never_a_super_admin(hub: Hub) -> None:
    admin = _super_admin(hub)
    member = hub.user()
    sid = hub.login(member)
    assert _grant(hub, admin, member.user_id, None).status_code == 201
    info = hub.get("/api/session", sid).json()
    assert (info["global_officer"], info["super_admin"]) == (True, False)
    assert info["officer_days"] == [d.id for d in hub.services.raid_days.raid_days]
    # The global tier still cannot hand out officer powers, bank grants or badges.
    assert hub.get("/api/admin/officer-grants", sid).status_code == 403
    assert _grant(hub, sid, member.user_id, "wed").status_code == 403
    assert hub.get("/api/admin/role-badges", sid).status_code == 403


def test_only_members_of_the_server_and_known_nights_can_be_granted(hub: Hub) -> None:
    admin = _super_admin(hub)
    gone = hub.user(in_guild=False)
    assert _grant(hub, admin, gone.user_id, "wed").status_code == 422
    assert _grant(hub, admin, hub.user().user_id, "fri").status_code == 422
    for odd in ("0", "12a", "1" * 21):
        assert hub.post("/api/admin/officer-grants", admin, {"discord_user_id": odd}).status_code == 422

    async def down(*_args: object, **_kwargs: object) -> None:
        raise DiscordError("down")

    hub.services.discord.guild_member = down  # type: ignore[method-assign]
    hub.services.discord.search_members = down  # type: ignore[method-assign]
    assert _grant(hub, admin, hub.user().user_id, "wed").status_code == 503
    assert hub.get("/api/admin/officer-grants/discord-members?q=a", admin).status_code == 503


def test_search_finds_server_members(hub: Hub) -> None:
    admin = _super_admin(hub)
    bob = hub.user(nick="Bobtoad")
    found = hub.get("/api/admin/officer-grants/discord-members?q=Bobt", admin)
    assert found.status_code == 200, found.text
    assert {"discord_user_id": str(bob.user_id), "username": bob.username, "display_name": "Bobtoad"} in found.json()


def test_officers_and_raiders_cannot_manage_officer_grants(hub: Hub) -> None:
    for roles in ((("global", "officer"),), (("wed", "officer"),), (("wed", "raider"),)):
        sid = hub.login(hub.user(*roles))
        assert hub.get("/api/admin/officer-grants", sid).status_code == 403
        assert hub.get("/api/admin/officer-grants/discord-members?q=a", sid).status_code == 403
        assert _grant(hub, sid, 1234, "wed").status_code == 403
        assert hub.delete("/api/admin/officer-grants/1", sid).status_code == 403
    assert hub.get("/api/admin/officer-grants", None).status_code == 401
