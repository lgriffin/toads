"""Role badges (docs/role-badges.md): the rules in RoleBadgeService, the routes, and the catalogue against the web
app's list and artwork."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from toads_api.role_badges.catalog import ROLE_BADGES
from toads_api.role_badges.repository import InMemoryRoleBadgeRepository
from toads_api.role_badges.service import RoleBadgeError, RoleBadgeService

from conftest import GUILD_ID, Hub, make_settings

ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------- rules


def test_a_member_earns_each_badge_their_roles_are_tied_to_once_in_catalogue_order() -> None:
    svc = RoleBadgeService(InMemoryRoleBadgeRepository())
    svc.tie(30, "Healers", "healer", by=1)
    svc.tie(31, "Wednesday raiders", "wednesday-toad", by=1)
    svc.tie(32, "Resto", "healer", by=1)
    assert [b.id for b in svc.earned({30, 31, 32, 99})] == ["wednesday-toad", "healer"]
    assert svc.earned({99}) == []


def test_links_are_listed_in_catalogue_order() -> None:
    svc = RoleBadgeService(InMemoryRoleBadgeRepository())
    svc.tie(30, "Tanks", "tank", by=1)
    svc.tie(31, "Sunday", "sunday-toad", by=1)
    assert [(v.role_name, v.badge.id) for v in svc.links()] == [("Sunday", "sunday-toad"), ("Tanks", "tank")]


def test_unknown_badge_duplicate_and_missing_tie_are_refused() -> None:
    svc = RoleBadgeService(InMemoryRoleBadgeRepository())
    with pytest.raises(RoleBadgeError) as info:
        svc.tie(30, "Tanks", "not-a-badge", by=1)
    assert info.value.status == 422
    svc.tie(30, "Tanks", "tank", by=1)
    with pytest.raises(RoleBadgeError) as info:
        svc.tie(30, "Tanks", "tank", by=1)
    assert info.value.status == 409
    svc.untie(30, "tank", by=1)
    with pytest.raises(RoleBadgeError) as info:
        svc.untie(30, "tank", by=1)
    assert info.value.status == 404


def test_a_retired_badge_earns_nothing() -> None:
    repo = InMemoryRoleBadgeRepository()
    repo.add(30, "retired-badge", "Old", by=1)
    svc = RoleBadgeService(repo)
    assert svc.earned({30}) == []
    assert svc.links() == []


# ---------------------------------------------------------------- catalogue


def test_catalogue_matches_the_web_app_and_has_artwork() -> None:
    ts = (ROOT / "apps/web/src/lib/role-badges.ts").read_text(encoding="utf-8")
    web = re.findall(r"\{ id: '([a-z0-9-]+)', name: '([^']+)', file: '([a-z0-9/-]+)'", ts)
    assert web == [(b.id, b.name, b.file) for b in ROLE_BADGES.values()]
    for b in ROLE_BADGES.values():
        for suffix in ("", "-badge"):
            assert (ROOT / f"apps/web/static/logos/{b.file}{suffix}.svg").is_file(), b.file


# ---------------------------------------------------------------- routes


def _super_admin(hub: Hub) -> str:
    user = hub.user()
    hub.services.settings = make_settings(super_admin_ids=str(user.user_id))
    return hub.login(user)


def _role(hub: Hub, role_id: int, name: str) -> None:
    hub.fake.guild_roles.add(role_id)
    hub.fake.role_names[role_id] = name


def test_admin_lists_the_catalogue_and_the_servers_member_roles(hub: Hub) -> None:
    _role(hub, 7001, "Healers")
    admin = _super_admin(hub)
    body = hub.get("/api/admin/role-badges", admin).json()
    assert [b["id"] for b in body["badges"]] == list(ROLE_BADGES)
    ids = {r["id"] for r in body["roles"]}
    assert "7001" in ids and str(GUILD_ID) not in ids  # @everyone is never offered
    assert {"id": "7001", "name": "Healers", "colour": None} in body["roles"]
    assert body["links"] == []


def test_tie_list_untie_and_the_members_badges(hub: Hub) -> None:
    _role(hub, 7001, "Healers")
    admin = _super_admin(hub)
    healer = hub.user(("sun", "raider"))
    healer.roles.add(7001)
    tied = hub.post("/api/admin/role-badges", admin, {"discord_role_id": "7001", "badge_id": "healer"})
    assert tied.status_code == 201, tied.text
    assert tied.json()["role_name"] == "Healers"
    assert (
        hub.post("/api/admin/role-badges", admin, {"discord_role_id": "7001", "badge_id": "healer"}).status_code == 409
    )
    listed = hub.get("/api/admin/role-badges", admin).json()["links"]
    assert [(link["discord_role_id"], link["badge"]["id"]) for link in listed] == [("7001", "healer")]
    sid = hub.login(healer)
    assert hub.get("/api/me/role-badges", sid).json() == [{"id": "healer", "name": "Healer", "file": "roles/healer"}]
    assert hub.delete("/api/admin/role-badges/7001/healer", admin).status_code == 204
    assert hub.delete("/api/admin/role-badges/7001/healer", admin).status_code == 404
    assert hub.delete("/api/admin/role-badges/not-a-role/healer", admin).status_code == 404


def test_role_ids_must_be_digits(hub: Hub) -> None:
    admin = _super_admin(hub)
    r = hub.post("/api/admin/role-badges", admin, {"discord_role_id": "12a", "badge_id": "tank"})
    assert r.status_code == 422


def test_when_discord_is_down_the_list_still_reads_and_tying_waits(hub: Hub) -> None:
    _role(hub, 7001, "Tanks")
    admin = _super_admin(hub)
    assert hub.post("/api/admin/role-badges", admin, {"discord_role_id": "7001", "badge_id": "tank"}).status_code == 201
    hub.fake.bot_in_server = False
    body = hub.get("/api/admin/role-badges", admin).json()
    assert body["roles"] is None
    assert body["links"][0]["role_name"] == "Tanks"
    r = hub.post("/api/admin/role-badges", admin, {"discord_role_id": "7001", "badge_id": "damage"})
    assert r.status_code == 503


def test_officers_and_raiders_cannot_manage_role_badges(hub: Hub) -> None:
    for roles in ((("global", "officer"),), (("wed", "raider"),)):
        sid = hub.login(hub.user(*roles))
        assert hub.get("/api/admin/role-badges", sid).status_code == 403
        assert hub.post("/api/admin/role-badges", sid, {"discord_role_id": "1", "badge_id": "tank"}).status_code == 403
        assert hub.delete("/api/admin/role-badges/1/tank", sid).status_code == 403
        assert hub.get("/api/me/role-badges", sid).json() == []
    assert hub.get("/api/me/role-badges", None).status_code == 401
