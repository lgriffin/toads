"""RBAC matrix over (tier x raid day x permission), including sibling-day denials (REQ-HUB-DAY-021)."""

import itertools
from pathlib import Path

import pytest
from toads_api.rbac import HubRole, Permission, Principal, RaidDaysConfig, can
from toads_api.rbac.permissions import ROLE_PERMISSIONS

DAYS = ("wed", "sun")
OFFICER_ONLY = {Permission.VIEW_OTHERS, Permission.VIEW_INSIGHTS, Permission.SYNC_LOGS, Permission.APPROVE_CLAIMS}


def test_matrix_matches_spec() -> None:
    assert ROLE_PERMISSIONS[HubRole.MEMBER] == {Permission.VIEW_GUILD_RAIDS}
    assert Permission.VIEW_OWN_PERFORMANCE in ROLE_PERMISSIONS[HubRole.TRIAL]
    assert Permission.UPLOAD_SCREENSHOTS not in ROLE_PERMISSIONS[HubRole.TRIAL]
    assert Permission.UPLOAD_SCREENSHOTS in ROLE_PERMISSIONS[HubRole.RAIDER]
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
