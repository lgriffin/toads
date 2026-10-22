"""View as (docs/admin.md "View as"): a super admin sees the hub, read only, as one raid night's raider or officer."""

from __future__ import annotations

from toads_api.rbac import HubRole, Permission, Principal, can
from toads_api.rbac.permissions import ViewAs

from conftest import Hub, make_settings


def _super_admin(hub: Hub) -> str:
    user = hub.user(("sun", "officer"))
    hub.services.settings = make_settings(super_admin_ids=str(user.user_id))
    return hub.login(user)


def test_only_super_admins_may_view_as_and_only_a_known_night() -> None:
    officer = Principal(member_id=1, global_officer=True)
    assert not can(officer, Permission.VIEW_AS)
    viewing = Principal(member_id=1, day_roles={"sun": HubRole.RAIDER}, viewing_as=ViewAs(HubRole.RAIDER, "sun"))
    assert can(viewing, Permission.VIEW_AS)  # going back
    assert not can(viewing, Permission.MANAGE_OFFICER_GRANTS)


def test_a_global_officer_may_not_view_as(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    assert hub.put("/api/admin/view-as/raider/sun", sid).status_code == 403
    assert hub.delete("/api/admin/view-as", sid).status_code == 403


def test_unknown_nights_and_roles_are_refused(hub: Hub) -> None:
    sid = _super_admin(hub)
    assert hub.put("/api/admin/view-as/raider/fri", sid).status_code == 404
    assert hub.put("/api/admin/view-as/super/sun", sid).status_code == 422
    assert hub.get("/api/session", sid).json()["view_as"] is None


def test_going_back_when_not_viewing_is_harmless(hub: Hub) -> None:
    sid = _super_admin(hub)
    assert hub.delete("/api/admin/view-as", sid).status_code == 204
    assert hub.get("/api/session", sid).json()["super_admin"]


def test_the_view_keeps_the_super_admins_identity_and_survives_a_role_refresh(hub: Hub) -> None:
    sid = _super_admin(hub)
    me = hub.get("/api/session", sid).json()
    hub.put("/api/admin/view-as/officer/wed", sid)
    hub.pass_time(hub.services.settings.role_refresh_seconds + 1)
    s = hub.get("/api/session", sid).json()
    assert (s["member_id"], s["display_name"]) == (me["member_id"], me["display_name"])
    assert s["view_as"]["role"] == "officer" and s["officer_days"] == ["wed"]
    assert s["day_roles"] == {"wed": "officer"}


def test_a_stored_view_stops_counting_once_they_are_no_longer_a_super_admin(hub: Hub) -> None:
    sid = _super_admin(hub)
    hub.put("/api/admin/view-as/raider/wed", sid)
    hub.services.settings = make_settings()
    s = hub.get("/api/session", sid).json()
    assert s["view_as"] is None and s["day_roles"] == {"sun": "officer"}


def test_switching_view_moves_straight_to_the_new_one(hub: Hub) -> None:
    sid = _super_admin(hub)
    hub.put("/api/admin/view-as/raider/wed", sid)
    assert hub.put("/api/admin/view-as/officer/sun", sid).status_code == 200
    assert hub.get("/api/session", sid).json()["day_roles"] == {"sun": "officer"}
