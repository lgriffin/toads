"""RBAC matrix over (tier x raid day x endpoint), including sibling-day denials (REQ-HUB-DAY-021).

The endpoint list is generated from the app's routes and their `require(...)` guards, so a new route is
covered the moment it exists. The expected outcome comes from SPEC below, a transcription of the build
spec's RBAC table, not from `can()`, so the test checks the implementation against the spec.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from toads_api.main import create_app
from toads_api.rbac import HubRole, Permission, Principal, RaidDaysConfig, can
from toads_api.rbac.deps import RouteRule, get_principal, route_rules
from toads_api.rbac.permissions import ROLE_PERMISSIONS

from conftest import Hub

DAYS = ("wed", "sun")
P = Permission
OFFICER_ONLY = {P.VIEW_OTHERS, P.VIEW_INSIGHTS, P.SYNC_LOGS, P.APPROVE_CLAIMS}

# The build spec's table: which tier holds which permission on its own raid day.
SPEC: dict[str, set[Permission]] = {
    "member": {P.VIEW_GUILD_RAIDS},
    "trial": {P.VIEW_GUILD_RAIDS, P.VIEW_OWN_PERFORMANCE, P.CLAIM_CHARACTER},
    "raider": {P.VIEW_GUILD_RAIDS, P.VIEW_OWN_PERFORMANCE, P.CLAIM_CHARACTER, P.UPLOAD_SCREENSHOTS},
    "officer": set(Permission),
}
TIERS = ("member", "trial", "raider", "officer", "global")
# Routes that are public by design: health, and the OAuth dance that creates the session.
PUBLIC = {"GET /healthz", "GET /auth/login", "GET /auth/callback", "POST /auth/logout"}


def principal(tier: str, own_day: str) -> Principal:
    if tier == "global":
        return Principal(member_id=1, global_officer=True)
    if tier == "member":
        return Principal(member_id=1)
    return Principal(member_id=1, day_roles={own_day: HubRole[tier.upper()]})


def expected_allowed(tier: str, own_day: str, permission: Permission, target_day: str | None) -> bool:
    if tier == "global":
        return True
    if target_day is None:
        # Guild-wide routes: officer powers are only ever held for a day, so a day officer counts as a raider.
        effective = "raider" if tier == "officer" else tier
    else:
        effective = tier if own_day == target_day else "member"
    return permission in SPEC[effective]


@dataclass(frozen=True)
class Case:
    tier: str
    own_day: str
    rule: RouteRule
    target_day: str | None

    @property
    def path(self) -> str:
        path = self.rule.path.replace("{day}", self.target_day or "")
        return re.sub(r"\{[a-z_]+\}", "999999", path)

    @property
    def sibling(self) -> bool:
        return self.target_day is not None and self.target_day != self.own_day

    def __str__(self) -> str:
        return f"{self.tier}@{self.own_day}-{self.rule.method}-{self.path}"


RULES, UNGUARDED = route_rules(create_app())


def matrix() -> list[Case]:
    cases = []
    for tier, own_day, rule in itertools.product(TIERS, DAYS, RULES):
        targets: tuple[str | None, ...] = DAYS if rule.scoped else (None,)
        cases += [Case(tier, own_day, rule, t) for t in targets]
    return cases


@pytest.fixture
def client_for(hub: Hub) -> Iterator[object]:
    def _for(p: Principal):
        async def _p() -> Principal:
            return p

        hub.app.dependency_overrides[get_principal] = _p
        return hub.client

    yield _for
    hub.app.dependency_overrides.clear()


@pytest.mark.parametrize("case", matrix(), ids=str)
def test_endpoint_matrix(case: Case, client_for) -> None:
    client = client_for(principal(case.tier, case.own_day))
    r = client.request(case.rule.method, case.path, json={} if case.rule.method in ("POST", "PUT", "PATCH") else None)
    allowed = expected_allowed(case.tier, case.own_day, case.rule.permission, case.target_day)
    if allowed:
        assert r.status_code not in (401, 403), r.text
    else:
        assert r.status_code == 403, r.text


def test_every_api_route_is_guarded() -> None:
    assert set(UNGUARDED) == PUBLIC


def test_officer_routes_are_scoped_and_have_sibling_denials() -> None:
    officer_rules = [r for r in RULES if r.permission in OFFICER_ONLY]
    assert {(r.method, r.path) for r in officer_rules} >= {
        ("POST", "/api/days/{day}/admin/sync"),
        ("GET", "/api/days/{day}/claims"),
        ("POST", "/api/days/{day}/claims/{claim_id}/approve"),
        ("POST", "/api/days/{day}/claims/{claim_id}/reject"),
        ("POST", "/api/days/{day}/claims/{claim_id}/reassign"),
    }
    assert all(r.scoped for r in officer_rules)
    for rule in officer_rules:
        assert any(c.rule == rule and c.tier == "officer" and c.sibling for c in matrix())


def test_matrix_matches_spec() -> None:
    for tier, perms in SPEC.items():
        assert ROLE_PERMISSIONS[HubRole[tier.upper()]] == perms
    for role in (HubRole.MEMBER, HubRole.TRIAL, HubRole.RAIDER):
        assert not (ROLE_PERMISSIONS[role] & OFFICER_ONLY)


@pytest.mark.parametrize(("own_day", "target_day", "permission"), list(itertools.product(DAYS, DAYS, OFFICER_ONLY)))
def test_day_officer_scoped_to_own_day(own_day: str, target_day: str, permission: Permission) -> None:
    officer = Principal(member_id=1, day_roles={own_day: HubRole.OFFICER})
    assert can(officer, permission, target_day) is (own_day == target_day)


@pytest.mark.parametrize(("day", "permission"), list(itertools.product(DAYS, Permission)))
def test_global_officer_everywhere(day: str, permission: Permission) -> None:
    assert can(Principal(member_id=1, global_officer=True), permission, day)


@pytest.mark.parametrize("permission", OFFICER_ONLY)
def test_day_officer_has_no_officer_powers_guild_wide(permission: Permission) -> None:
    assert not can(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}), permission, None)


def test_role_mapping_takes_highest(tmp_path: Path) -> None:
    cfg_file = tmp_path / "raid_days.yaml"
    cfg_file.write_text(
        "global_officer_roles: [900]\n"
        "raid_days:\n"
        "  - {id: wed, name: Wednesday, trial_roles: [10], raider_roles: [11], officer_roles: [12]}\n"
        "  - {id: sun, name: Sunday, raider_roles: [21]}\n"
    )
    cfg = RaidDaysConfig.load(cfg_file)
    p = cfg.principal_for(5, {10, 11, 21})
    assert p.day_roles == {"wed": HubRole.RAIDER, "sun": HubRole.RAIDER}
    assert not p.global_officer
    assert cfg.principal_for(5, {900}).global_officer
    assert cfg.principal_for(5, {999}).day_roles == {}


def test_home_day_prefers_highest_role_then_config_order() -> None:
    assert Principal(member_id=1).home_day() is None
    assert Principal(member_id=1, day_roles={"wed": HubRole.TRIAL, "sun": HubRole.RAIDER}).home_day() == "sun"
    assert Principal(member_id=1, day_roles={"wed": HubRole.RAIDER, "sun": HubRole.RAIDER}).home_day() == "wed"
