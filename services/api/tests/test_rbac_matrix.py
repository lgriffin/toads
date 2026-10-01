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
from toads_api.rbac.permissions import GRANTABLE, ROLE_PERMISSIONS, SUPER_ADMIN_ONLY

from conftest import Hub

DAYS = ("wed", "sun")
P = Permission
OFFICER_ONLY = {
    P.VIEW_OTHERS,
    P.VIEW_INSIGHTS,
    P.SYNC_LOGS,
    P.APPROVE_CLAIMS,
    P.MANAGE_RECRUITMENT,
    P.MANAGE_POSTS,
    P.MANAGE_HIGHLIGHTS,
    P.IMPORT_BANK_SNAPSHOT,
    P.MANAGE_BANK,
}

# The build spec's table: which tier holds which permission on its own raid day.
# Every guild member may see the bank and ask it for items (docs/bank.md).
BANK = {P.VIEW_BANK, P.REQUEST_BANK_ITEMS}
SPEC: dict[str, set[Permission]] = {
    "member": {P.VIEW_GUILD_RAIDS, P.APPLY, *BANK},
    "trial": {P.VIEW_GUILD_RAIDS, P.APPLY, P.VIEW_OWN_PERFORMANCE, P.CLAIM_CHARACTER, *BANK},
    "raider": {
        *BANK,
        P.VIEW_GUILD_RAIDS,
        P.APPLY,
        P.VIEW_OWN_PERFORMANCE,
        P.CLAIM_CHARACTER,
        P.UPLOAD_SCREENSHOTS,
        P.SUBMIT_HIGHLIGHT,
    },
    # Everything but managing grants and tokens, which is the super admins' alone (docs/admin.md).
    "officer": set(Permission) - {P.MANAGE_GRANTS},
}
# Super admins (TOADS_SUPER_ADMIN_IDS, docs/admin.md) hold everything a global officer has, and alone manage grants.
SUPER_ONLY = {P.MANAGE_GRANTS}
# What a super admin may grant one Discord user (docs/bank.md "Grants"): the bank's upkeep, on one raid day's banks
# or on every bank. A grant only ever counts on a raid day's routes, never on guild-wide (global tier) ones.
GRANTS = {P.IMPORT_BANK_SNAPSHOT, P.MANAGE_BANK}
# "grantee": a plain member granted both bank permissions on their own day.
# "super": a super admin from configuration; "break_glass": the break-glass admin, a super admin by another name.
TIERS = ("member", "trial", "raider", "officer", "global", "grantee", "super", "break_glass")
# Routes that are public by design: health, and the OAuth dance that creates the session.
PUBLIC = {
    "GET /healthz",
    "GET /auth/login",
    "GET /auth/callback",
    "POST /auth/logout",
    # The outward story and recruitment needs, for visitors.
    "GET /api/public/story",
    "GET /api/public/recruitment",
}
GLOBAL_ADMIN_PREFIX = "/api/admin/"
# The bots' and the worker's routes: guarded by the service token (test_community.py, test_bots.py,
# test_hub_sheets.py), not by a member's permission; and ToadsBank's events, by the bank's token (test_bank.py).
SERVICE_PREFIXES = ("/api/bot/", "/api/bots", "/api/worker/", "/api/bank/events")


def principal(tier: str, own_day: str) -> Principal:
    if tier == "super":
        return Principal(member_id=1, super_admin=True)
    if tier == "break_glass":
        return Principal(member_id=1, break_glass=True)
    if tier == "global":
        return Principal(member_id=1, global_officer=True)
    if tier == "member":
        return Principal(member_id=1)
    if tier == "grantee":
        return Principal(member_id=1, grants=frozenset((p, own_day) for p in GRANTS))
    return Principal(member_id=1, day_roles={own_day: HubRole[tier.upper()]})


def expected_allowed(tier: str, own_day: str, permission: Permission, target_day: str | None) -> bool:
    if tier in ("super", "break_glass"):
        return True
    if permission in SUPER_ONLY:
        return False
    if tier == "global":
        return True
    if tier == "grantee":
        return permission in SPEC["member"] or (target_day == own_day and permission in GRANTS)
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
    assert {r for r in UNGUARDED if not r.split(" ", 1)[1].startswith(SERVICE_PREFIXES)} == PUBLIC


def test_officer_routes_are_scoped_and_have_sibling_denials() -> None:
    officer_rules = [r for r in RULES if r.permission in OFFICER_ONLY]
    assert {(r.method, r.path) for r in officer_rules} >= {
        ("POST", "/api/days/{day}/admin/sync"),
        ("GET", "/api/days/{day}/claims"),
        ("POST", "/api/days/{day}/claims/{claim_id}/approve"),
        ("POST", "/api/days/{day}/claims/{claim_id}/reject"),
        ("POST", "/api/days/{day}/claims/{claim_id}/reassign"),
    }
    scoped = [r for r in officer_rules if r.scoped]
    assert all("{day}" in r.path for r in scoped)
    for rule in scoped:
        assert any(c.rule == rule and c.tier == "officer" and c.sibling for c in matrix())
    # Guild-wide officer routes live under /api/admin and are the global tier's (and so the super admins') alone: a
    # day officer counts as a raider there.
    for rule in (r for r in officer_rules if not r.scoped):
        assert rule.path.startswith(GLOBAL_ADMIN_PREFIX)
        assert {
            c.tier for c in matrix() if c.rule == rule and expected_allowed(c.tier, c.own_day, rule.permission, None)
        } == {"global", "super", "break_glass"}


def test_grant_and_token_routes_are_the_super_admins_alone() -> None:
    super_rules = [r for r in RULES if r.permission in SUPER_ONLY]
    assert {(r.method, r.path) for r in super_rules} == {
        ("POST", "/api/admin/bank/grants"),
        ("DELETE", "/api/admin/bank/grants/{grant_id}"),
        ("GET", "/api/admin/bank/tokens"),
        ("POST", "/api/admin/bank/tokens"),
        ("DELETE", "/api/admin/bank/tokens/{token_id}"),
    }
    for rule in super_rules:
        assert not rule.scoped
        assert {
            c.tier for c in matrix() if c.rule == rule and expected_allowed(c.tier, c.own_day, rule.permission, None)
        } == {"super", "break_glass"}
    # Global officers still list grants (docs/admin.md).
    assert ("GET", "/api/admin/bank/grants", P.MANAGE_BANK) in {(r.method, r.path, r.permission) for r in RULES}


def test_only_the_banks_upkeep_can_be_granted() -> None:
    assert GRANTABLE == GRANTS
    assert SUPER_ADMIN_ONLY == SUPER_ONLY
    assert not (GRANTS & SUPER_ONLY)
    assert GRANTS <= OFFICER_ONLY  # officers inherit every grantable permission through their role


@pytest.mark.parametrize(("own_day", "target_day"), list(itertools.product(DAYS, DAYS)))
def test_a_day_grant_is_scoped_to_its_day_and_a_dayless_grant_to_every_day(own_day: str, target_day: str) -> None:
    for permission in GRANTS:
        day_grant = Principal(member_id=1, grants=frozenset({(permission, own_day)}))
        assert can(day_grant, permission, target_day) is (own_day == target_day)
        assert can(Principal(member_id=1, grants=frozenset({(permission, None)})), permission, target_day)


@pytest.mark.parametrize("permission", sorted(GRANTS))
def test_a_grant_never_reaches_a_guild_wide_route(permission: Permission) -> None:
    assert not can(Principal(member_id=1, grants=frozenset({(permission, None)})), permission, None)


def test_matrix_matches_spec() -> None:
    for tier, perms in SPEC.items():
        assert ROLE_PERMISSIONS[HubRole[tier.upper()]] == perms
    for role in (HubRole.MEMBER, HubRole.TRIAL, HubRole.RAIDER):
        assert not (ROLE_PERMISSIONS[role] & OFFICER_ONLY)


@pytest.mark.parametrize(("own_day", "target_day", "permission"), list(itertools.product(DAYS, DAYS, OFFICER_ONLY)))
def test_day_officer_scoped_to_own_day(own_day: str, target_day: str, permission: Permission) -> None:
    officer = Principal(member_id=1, day_roles={own_day: HubRole.OFFICER})
    assert can(officer, permission, target_day) is (own_day == target_day)


@pytest.mark.parametrize(("day", "permission"), list(itertools.product(DAYS, set(Permission) - SUPER_ONLY)))
def test_global_officer_everywhere(day: str, permission: Permission) -> None:
    assert can(Principal(member_id=1, global_officer=True), permission, day)


@pytest.mark.parametrize(("day", "permission"), list(itertools.product((*DAYS, None), Permission)))
def test_super_admin_and_break_glass_hold_everything(day: str | None, permission: Permission) -> None:
    assert can(Principal(member_id=1, super_admin=True), permission, day)
    assert can(Principal(member_id=1, break_glass=True), permission, day)


@pytest.mark.parametrize("day", (*DAYS, None))
def test_nobody_below_a_super_admin_manages_grants(day: str | None) -> None:
    every_grant = frozenset((p, d) for p in Permission for d in (*DAYS, None))
    for p in (
        Principal(member_id=1, global_officer=True),
        Principal(member_id=1, day_roles=dict.fromkeys(DAYS, HubRole.OFFICER)),
        Principal(member_id=1, grants=every_grant),
    ):
        assert not can(p, P.MANAGE_GRANTS, day)


def test_super_admin_is_a_global_officer_and_break_glass_a_super_admin() -> None:
    assert Principal(member_id=1, super_admin=True).global_officer
    glass = Principal(member_id=1, break_glass=True)
    assert glass.super_admin and glass.global_officer


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
