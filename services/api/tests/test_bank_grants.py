"""Bank grants and officer tokens (docs/bank.md "Grants", docs/admin.md): the rules over an in-memory repository, the
hub-db repository, the routes, and how a grant or a super admin reaches require(...) through the Principal. The flows
end to end are in tests/step_defs/test_hub_bank.py (REQ-HUB-BANK-032..043, REQ-HUB-RBAC-003..004)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hub_db import EVERY_DAY, AuditEntry, BankGrant, BankGrantToken, Member
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from toads_api.bank_grants import sql as grants_sql
from toads_api.bank_grants.repository import InMemoryBankGrantRepository, NewGrant, Redeemer
from toads_api.bank_grants.routes import REDEEM_ATTEMPTS
from toads_api.bank_grants.service import (
    DEFAULT_DAYS,
    GRANTABLE,
    MINTED_PREFIX,
    REFUSED,
    BankGrantService,
    GrantError,
    hash_token,
)
from toads_api.bank_grants.sql import SqlBankGrantRepository
from toads_api.rbac import HubRole, Permission, Principal, can
from toads_api.rbac.deps import BREAK_GLASS_ACTION, elevate
from toads_api.rbac.permissions import GRANTABLE as GRANTABLE_PERMISSIONS

from conftest import Hub, make_settings

DAYS = ("wed", "sun")
START = datetime(2026, 1, 7, 19, 30, tzinfo=UTC)
TADPOLE = Redeemer(discord_user_id=42, display_name="Tadpole", member_id=7)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now


def service(clock: Clock | None = None) -> tuple[BankGrantService, InMemoryBankGrantRepository]:
    repo = InMemoryBankGrantRepository(names={1: "Croak"})
    return BankGrantService(repo, DAYS, clock=clock or Clock()), repo


def test_the_service_and_the_rbac_layer_agree_on_what_can_be_granted() -> None:
    assert set(GRANTABLE) == {p.value for p in GRANTABLE_PERMISSIONS}
    assert {Permission.IMPORT_BANK_SNAPSHOT, Permission.MANAGE_BANK} == GRANTABLE_PERMISSIONS


def test_a_grant_is_stored_once_with_who_granted_it() -> None:
    grants, _ = service()
    first, created = grants.grant(42, " Tadpole ", "manage_bank", "wed", granted_by=1)
    again, created_again = grants.grant(42, "Tadpole", "manage_bank", "wed", granted_by=1)
    assert (created, created_again) == (True, False)
    assert again == first
    assert (first.display_name, first.granted_by, first.granted_by_name) == ("Tadpole", 1, "Croak")
    everywhere, created = grants.grant(42, "Tadpole", "manage_bank", None, granted_by=1)
    assert created and everywhere.id != first.id
    assert grants.held_by(42) == {("manage_bank", "wed"), ("manage_bank", None)}
    assert grants.held_by(43) == frozenset()


@pytest.mark.parametrize(
    ("permission", "day", "user"),
    [("manage_posts", "wed", 42), ("view_bank", None, 42), ("manage_bank", "fri", 42), ("manage_bank", None, 0)],
)
def test_only_bank_upkeep_on_a_known_day_can_be_granted(permission: str, day: str | None, user: int) -> None:
    grants, repo = service()
    with pytest.raises(GrantError) as info:
        grants.grant(user, "x", permission, day, granted_by=1)
    assert info.value.status == 422 and repo.grants == {}


def test_a_revoked_grant_opens_nothing_and_a_second_revoke_is_404() -> None:
    grants, repo = service()
    record, _ = grants.grant(42, "Tadpole", "import_bank_snapshot", "sun", granted_by=1)
    assert grants.revoke(record.id, revoked_by=1) == record
    assert grants.held_by(42) == frozenset() and repo.revoked == [(record.id, 1)]
    with pytest.raises(GrantError) as info:
        grants.revoke(record.id, revoked_by=1)
    assert info.value.status == 404


def test_a_grant_for_a_raid_day_no_longer_configured_opens_nothing() -> None:
    repo = InMemoryBankGrantRepository()
    BankGrantService(repo, ("wed", "fri")).grant(42, "Tadpole", "manage_bank", "fri", granted_by=1)
    assert BankGrantService(repo, DAYS).held_by(42) == frozenset()


# ------------------------------------------------------------------ tokens


def test_a_minted_token_is_shown_once_and_only_its_hash_is_kept() -> None:
    grants, repo = service()
    minted = grants.mint(["manage_bank", "import_bank_snapshot"], "wed", minted_by=1, note=" for Tadpole ")
    assert minted.token.startswith(MINTED_PREFIX) and len(minted.token) > 40
    record = minted.record
    assert record.permissions == ("import_bank_snapshot", "manage_bank")
    assert (record.raid_day, record.note, record.minted_by_name, record.max_uses, record.uses) == (
        "wed",
        "for Tadpole",
        "Croak",
        1,
        0,
    )
    assert record.expires_at - record.minted_at == timedelta(days=DEFAULT_DAYS)
    assert record.status(START) == "active"
    stored_hash, _ = repo.minted[record.id]
    assert stored_hash == hash_token(minted.token) and minted.token not in stored_hash
    assert grants.mint(["manage_bank"], None, minted_by=1).token != minted.token


@pytest.mark.parametrize(
    ("permissions", "day", "days", "uses"),
    [
        ([], None, 7, 1),
        (["manage_posts"], None, 7, 1),
        (["manage_bank"], "fri", 7, 1),
        (["manage_bank"], None, 0, 1),
        (["manage_bank"], None, 31, 1),
        (["manage_bank"], None, 7, 0),
        (["manage_bank"], None, 7, 26),
    ],
)
def test_a_token_names_only_bank_upkeep_on_a_known_day_for_a_bounded_time(
    permissions: list[str], day: str | None, days: int, uses: int
) -> None:
    grants, repo = service()
    with pytest.raises(GrantError) as info:
        grants.mint(permissions, day, minted_by=1, days=days, max_uses=uses)
    assert info.value.status == 422 and repo.minted == {}


def test_redeeming_gives_the_named_grants_once() -> None:
    grants, _ = service()
    minted = grants.mint(["import_bank_snapshot", "manage_bank"], "sun", minted_by=1)
    record, given = grants.redeem(f"  {minted.token} ", TADPOLE)
    assert (record.uses, record.used_by, record.status(START)) == (1, 42, "used")
    assert {(g.permission, g.raid_day, g.granted_by) for g in given} == {
        ("import_bank_snapshot", "sun", 1),
        ("manage_bank", "sun", 1),
    }
    assert grants.held_by(42) == {("import_bank_snapshot", "sun"), ("manage_bank", "sun")}
    with pytest.raises(GrantError) as info:
        grants.redeem(minted.token, Redeemer(43, "Ribbit", 8))
    assert (info.value.status, info.value.message) == (400, REFUSED)
    assert grants.held_by(43) == frozenset()


def test_a_token_minted_for_several_uses_runs_out() -> None:
    grants, _ = service()
    minted = grants.mint(["manage_bank"], None, minted_by=1, max_uses=2)
    grants.redeem(minted.token, Redeemer(42, "Tadpole", 7))
    record, _ = grants.redeem(minted.token, Redeemer(43, "Ribbit", 8))
    assert record.status(START) == "used"
    with pytest.raises(GrantError):
        grants.redeem(minted.token, Redeemer(44, "Croak", 9))


def test_wrong_expired_used_and_revoked_tokens_all_get_the_same_answer() -> None:
    clock = Clock()
    grants, _ = service(clock)
    used = grants.mint(["manage_bank"], None, minted_by=1)
    grants.redeem(used.token, TADPOLE)
    revoked = grants.mint(["manage_bank"], None, minted_by=1)
    grants.revoke_token(revoked.record.id, revoked_by=1)
    expiring = grants.mint(["manage_bank"], None, minted_by=1, days=1)
    clock.now = START + timedelta(days=1)
    answers = set()
    for token in (used.token, revoked.token, expiring.token, MINTED_PREFIX + "x" * 43, "short", "x" * 201):
        with pytest.raises(GrantError) as info:
            grants.redeem(token, Redeemer(43, "Ribbit", 8))
        answers.add((info.value.status, info.value.message))
    assert answers == {(400, REFUSED)}
    assert grants.held_by(43) == frozenset()


def test_only_a_token_that_could_still_be_redeemed_can_be_revoked() -> None:
    clock = Clock()
    grants, _ = service(clock)
    with pytest.raises(GrantError) as info:
        grants.revoke_token(99, revoked_by=1)
    assert info.value.status == 404
    minted = grants.mint(["manage_bank"], "wed", minted_by=1)
    grants.redeem(minted.token, TADPOLE)
    with pytest.raises(GrantError) as info:
        grants.revoke_token(minted.record.id, revoked_by=1)
    assert info.value.status == 409 and "used" in info.value.message
    # A revoke never takes back grants a token already gave.
    assert grants.held_by(42) == {("manage_bank", "wed")}
    open_token = grants.mint(["manage_bank"], "wed", minted_by=1)
    grants.revoke_token(open_token.record.id, revoked_by=1)
    assert [t.status(clock()) for t in grants.tokens()] == ["used", "revoked"]


# ------------------------------------------------------------------ hub-db


def test_the_sql_repository_keeps_grants_and_audits_them(hub: Hub) -> None:
    with hub.db.begin() as db:
        granter = Member(discord_user_id=900, display_name="Croak")
        db.add(granter)
        db.flush()
        granter_id = granter.id
    grants = BankGrantService(SqlBankGrantRepository(hub.db), DAYS)
    record, created = grants.grant(42, "Tadpole", "import_bank_snapshot", "wed", granted_by=granter_id)
    assert created and record.granted_by_name == "Croak"
    again, created_again = grants.grant(42, "Tadpole", "import_bank_snapshot", "wed", granted_by=granter_id)
    assert (again.id, again.granted_by_name, created_again) == (record.id, "Croak", False)
    everywhere, _ = grants.grant(42, "Tadpole", "import_bank_snapshot", None, granted_by=granter_id)
    assert [g.id for g in grants.all_grants()] == [record.id, everywhere.id]
    assert grants.held_by(42) == {("import_bank_snapshot", "wed"), ("import_bank_snapshot", None)}
    grants.revoke(record.id, revoked_by=granter_id)
    assert grants.held_by(42) == {("import_bank_snapshot", None)}
    with hub.db() as db:
        assert db.scalars(select(BankGrant.id)).all() == [everywhere.id]
        actions = [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert actions == [("bank.grant", "wed"), ("bank.grant", None), ("bank.revoke", "wed")]


def test_every_bank_is_stored_as_a_sentinel_so_the_unique_constraint_holds(hub: Hub) -> None:
    grants = BankGrantService(SqlBankGrantRepository(hub.db), DAYS)
    grants.grant(42, "Tadpole", "manage_bank", None, granted_by=_minter(hub))
    with hub.db() as db:
        assert db.scalars(select(BankGrant.raid_day)).all() == [EVERY_DAY]
    with pytest.raises(IntegrityError), hub.db.begin() as db:
        db.add(BankGrant(discord_user_id=42, display_name="Tadpole", permission="manage_bank", raid_day=EVERY_DAY))
        db.flush()


def test_a_grant_inserted_concurrently_is_returned_not_duplicated(hub: Hub, monkeypatch: pytest.MonkeyPatch) -> None:
    """Qodo 4152357932: two grants of the same thing at once. The loser's insert fails the unique constraint, and the
    retry finds the winner's row."""
    with hub.db.begin() as db:
        db.add(BankGrant(discord_user_id=42, display_name="Tadpole", permission="manage_bank", raid_day="wed"))
    real = grants_sql._existing
    misses = iter([True])

    def racing(db: Session, grant: NewGrant) -> BankGrant | None:
        # The first look happens before the other request commits, so it sees nothing.
        return None if next(misses, False) else real(db, grant)

    monkeypatch.setattr(grants_sql, "_existing", racing)
    record, created = SqlBankGrantRepository(hub.db).add(NewGrant(42, "Tadpole", "manage_bank", "wed", None))
    assert not created
    with hub.db() as db:
        assert db.scalars(select(BankGrant.id)).all() == [record.id]


def _minter(hub: Hub) -> int:
    with hub.db.begin() as db:
        member = Member(discord_user_id=900, display_name="Croak")
        db.add(member)
        db.flush()
        return member.id


def test_the_sql_repository_keeps_token_hashes_and_audits_mint_redeem_and_revoke(hub: Hub) -> None:
    clock = Clock()
    minter = _minter(hub)
    with hub.db.begin() as db:
        redeemer = Member(discord_user_id=42, display_name="Tadpole")
        db.add(redeemer)
        db.flush()
        redeemer_id = redeemer.id
    grants = BankGrantService(SqlBankGrantRepository(hub.db), DAYS, clock=clock)
    minted = grants.mint(["import_bank_snapshot", "manage_bank"], "wed", minted_by=minter, note="for Tadpole")
    assert minted.record.minted_by_name == "Croak"
    with hub.db() as db:
        row = db.get(BankGrantToken, minted.record.id)
        assert row is not None and row.token_hash == hash_token(minted.token)
        assert minted.token not in {row.token_hash, row.note}
    record, given = grants.redeem(minted.token, Redeemer(42, "Tadpole", redeemer_id))
    assert (record.uses, record.used_by, record.used_at) == (1, 42, START)
    assert {(g.permission, g.raid_day, g.granted_by_name) for g in given} == {
        ("import_bank_snapshot", "wed", "Croak"),
        ("manage_bank", "wed", "Croak"),
    }
    assert grants.held_by(42) == {("import_bank_snapshot", "wed"), ("manage_bank", "wed")}
    with pytest.raises(GrantError):
        grants.redeem(minted.token, Redeemer(42, "Tadpole", redeemer_id))
    spare = grants.mint(["manage_bank"], None, minted_by=minter)
    clock.now = START + timedelta(days=DEFAULT_DAYS)
    with pytest.raises(GrantError):
        grants.redeem(spare.token, Redeemer(42, "Tadpole", redeemer_id))
    with pytest.raises(GrantError) as info:
        grants.revoke_token(spare.record.id, revoked_by=minter)
    assert info.value.status == 409
    clock.now = START
    grants.revoke_token(spare.record.id, revoked_by=minter)
    assert [(t.id, t.status(START)) for t in grants.tokens()] == [
        (spare.record.id, "revoked"),
        (minted.record.id, "used"),
    ]
    with hub.db() as db:
        rows = [
            (a.action, a.actor_member_id, a.target, a.detail)
            for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))
        ]
    token_rows = [r for r in rows if r[0].startswith("bank.token")]
    assert [r[:3] for r in token_rows] == [
        ("bank.token_minted", minter, f"bank token {minted.record.id}"),
        ("bank.token_redeemed", redeemer_id, f"bank token {minted.record.id}"),
        ("bank.token_minted", minter, f"bank token {spare.record.id}"),
        ("bank.token_revoked", minter, f"bank token {spare.record.id}"),
    ]
    assert all(f"bank grant {g.id}" in (token_rows[1][3] or "") for g in given)
    # Grants from a token are audited once, under the token, not as bank.grant rows by the minter.
    assert not [r for r in rows if r[0] == "bank.grant"]


# --------------------------------------------------------------- the routes


def signed_in(hub: Hub, *roles: tuple[str, str], **settings: object) -> tuple[str, int]:
    user = hub.user(*roles, nick="Croak")
    if settings:
        hub.services.settings = make_settings(**{k: str(user.user_id) if v is True else v for k, v in settings.items()})
    return hub.login(user), user.user_id


def test_global_officers_list_grants_but_only_super_admins_grant_and_mint(hub: Hub) -> None:
    officer, _ = signed_in(hub, ("global", "officer"))
    assert hub.get("/api/admin/bank/grants", officer).status_code == 200
    assert (
        hub.post("/api/admin/bank/grants", officer, {"discord_user_id": "42", "permission": "manage_bank"}).status_code
        == 403
    )
    assert hub.post("/api/admin/bank/tokens", officer, {"permissions": ["manage_bank"]}).status_code == 403
    assert hub.get("/api/admin/bank/tokens", officer).status_code == 403
    assert hub.delete("/api/admin/bank/tokens/1", officer).status_code == 403


def test_a_super_admin_mints_lists_and_revokes_and_a_member_redeems_on_the_site(hub: Hub) -> None:
    admin, _ = signed_in(hub, super_admin_ids=True)
    minted = hub.post("/api/admin/bank/tokens", admin, {"permissions": ["manage_bank"], "raid_day": "wed"})
    assert minted.status_code == 201, minted.text
    body = minted.json()
    assert body["token"].startswith(MINTED_PREFIX) and body["status"] == "active"
    listed = hub.get("/api/admin/bank/tokens", admin).json()
    assert [t["id"] for t in listed] == [body["id"]] and "token" not in listed[0]
    assert body["token"] not in hub.get("/api/admin/bank/tokens", admin).text
    member = hub.login(hub.user(("wed", "raider")))
    r = hub.post("/api/bank/redeem", member, {"token": body["token"]})
    assert r.status_code == 200, r.text
    assert [(g["permission"], g["raid_day"]) for g in r.json()["grants"]] == [("manage_bank", "wed")]
    assert hub.get("/api/admin/bank/tokens", admin).json()[0]["status"] == "used"
    assert hub.delete(f"/api/admin/bank/tokens/{body['id']}", admin).status_code == 409


def test_refused_redemptions_read_alike_and_are_rate_limited(hub: Hub) -> None:
    member = hub.login(hub.user(("wed", "raider")))
    for _ in range(REDEEM_ATTEMPTS):
        r = hub.post("/api/bank/redeem", member, {"token": MINTED_PREFIX + "guess-guess-guess"})
        assert (r.status_code, r.json()["detail"]) == (400, REFUSED)
    assert hub.post("/api/bank/redeem", member, {"token": "anything-at-all"}).status_code == 429


def test_the_break_glass_admin_is_a_super_admin_shown_and_audited(hub: Hub) -> None:
    session, _ = signed_in(hub, break_glass_admin_id=True)
    shown = hub.get("/api/session", session).json()
    assert (shown["super_admin"], shown["break_glass"]) == (True, True)
    minted = hub.post("/api/admin/bank/tokens", session, {"permissions": ["import_bank_snapshot"]})
    assert minted.status_code == 201, minted.text
    hub.get("/api/admin/bank/tokens", session)
    with hub.db() as db:
        marked = [(a.action, a.target) for a in db.scalars(select(AuditEntry)) if a.action == BREAK_GLASS_ACTION]
    # Changes are marked; reads are not.
    assert marked == [(BREAK_GLASS_ACTION, "POST /api/admin/bank/tokens")]
    plain = hub.login(hub.user())
    assert hub.get("/api/session", plain).json()["break_glass"] is False


# --------------------------------------------------------------- the check


def granted(*grants: tuple[Permission, str | None]) -> Principal:
    return Principal(member_id=1, grants=frozenset(grants))


def test_a_day_grant_opens_that_days_routes_only() -> None:
    p = granted((Permission.IMPORT_BANK_SNAPSHOT, "wed"))
    assert can(p, Permission.IMPORT_BANK_SNAPSHOT, "wed")
    assert not can(p, Permission.IMPORT_BANK_SNAPSHOT, "sun")
    assert not can(p, Permission.MANAGE_BANK, "wed")
    assert not p.unbound(Permission.IMPORT_BANK_SNAPSHOT)


def test_a_grant_with_no_day_opens_every_days_routes_and_every_bank() -> None:
    p = granted((Permission.MANAGE_BANK, None))
    assert all(can(p, Permission.MANAGE_BANK, day) for day in DAYS)
    assert p.unbound(Permission.MANAGE_BANK) and not p.unbound(Permission.IMPORT_BANK_SNAPSHOT)


def test_a_grant_never_opens_the_global_tier_or_anything_but_the_bank() -> None:
    p = granted((Permission.MANAGE_BANK, None), (Permission.MANAGE_POSTS, None), (Permission.SYNC_LOGS, "wed"))
    # /api/admin/... checks guild-wide: grants count only on a raid day taken from the path.
    assert not can(p, Permission.MANAGE_BANK)
    assert not can(p, Permission.MANAGE_POSTS, "wed")
    assert not can(p, Permission.SYNC_LOGS, "wed")


def test_super_admins_and_the_break_glass_admin_come_from_configuration_only() -> None:
    settings = make_settings(super_admin_ids=" 41, 42 ", break_glass_admin_id="43")
    assert settings.super_admins() == {41, 42}
    assert make_settings(break_glass_admin_id=" ").break_glass_admin_id is None
    plain = Principal(member_id=1, discord_user_id=40)
    assert elevate(settings, plain) == plain
    listed = elevate(settings, Principal(member_id=1, discord_user_id=42))
    assert (listed.super_admin, listed.global_officer, listed.break_glass) == (True, True, False)
    glass = elevate(settings, Principal(member_id=1, discord_user_id=43))
    assert (glass.super_admin, glass.global_officer, glass.break_glass) == (True, True, True)
    # Not even a global officer's Discord role makes a super admin.
    assert not elevate(settings, Principal(member_id=1, discord_user_id=40, global_officer=True)).super_admin
    assert elevate(settings, Principal(member_id=1)) == Principal(member_id=1)


@pytest.mark.parametrize("ids", ["abc", "42,,43", "1" * 21])
def test_the_super_admin_list_must_be_discord_ids(ids: str) -> None:
    with pytest.raises(ValueError, match="super_admin_ids"):
        make_settings(super_admin_ids=ids)


def test_officers_inherit_every_grantable_permission_without_a_grant() -> None:
    day_officer = Principal(member_id=1, day_roles={"wed": HubRole.OFFICER})
    for permission in GRANTABLE_PERMISSIONS:
        assert can(day_officer, permission, "wed") and not can(day_officer, permission, "sun")
        assert all(can(Principal(member_id=1, global_officer=True), permission, day) for day in DAYS)
    # A grant adds to an officer's own days; it never narrows them.
    both = Principal(
        member_id=1, day_roles={"wed": HubRole.OFFICER}, grants=frozenset({(Permission.MANAGE_BANK, "sun")})
    )
    assert can(both, Permission.MANAGE_BANK, "wed") and can(both, Permission.MANAGE_BANK, "sun")
