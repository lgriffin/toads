"""The guild-report sync (REQ-DEV-OPS-004): new guild reports analysed in batches, newest first."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenario, then, when
from toads_worker.jobs import sync
from toads_worker.settings import Settings

FEATURES = Path(__file__).resolve().parents[3] / "tests" / "features"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": SecretStr("postgresql+psycopg://u:p@localhost/db"),
        "redis_url": "redis://localhost",
        "wcl_client_id": "id",
        "wcl_client_secret": SecretStr("replace-me"),
        "wcl_guild_id": 1,
        "credentials_keys": SecretStr("replace-me"),
    }
    values.update(overrides)
    return Settings(**values)


class FakeRaids:
    """Stands in for wcl_app.RaidService: the guild's reports newest first, the stored codes and the analyses run."""

    def __init__(self, remote: list[str], stored: set[str], broken: set[str] | None = None) -> None:
        self.remote = remote
        self.stored = set(stored)
        self.broken = broken or set()
        self.analysed: list[str] = []
        self.guilds: list[int] = []

    def guild_reports(self, guild_id: int) -> list[dict[str, Any]]:
        self.guilds.append(guild_id)
        return [{"code": code} for code in self.remote]

    def imported_codes(self) -> set[str]:
        return set(self.stored)

    def analyze_and_save(self, report_id: str, *, progress: Any = None) -> object:
        self.analysed.append(report_id)
        if report_id in self.broken:
            raise RuntimeError(f"{report_id} has no fights")
        self.stored.add(report_id)
        return object()


def test_new_report_codes_keep_the_order_given() -> None:
    assert sync.new_report_codes(["c", "b", "c", "a"], ["b"]) == ["c", "a"]


def test_sync_imports_everything_new_newest_first_when_it_fits_one_batch() -> None:
    raids = FakeRaids(["A", "B", "C"], stored=set())
    result = sync.sync_guild_reports(_settings(wcl_guild_id=42), raids=raids)
    assert raids.analysed == ["A", "B", "C"]
    assert raids.guilds == [42]
    assert result == {"imported": ["A", "B", "C"], "failed": {}, "remaining": 0}


def test_reports_that_never_analyse_do_not_hold_back_older_ones() -> None:
    raids = FakeRaids(["A", "B", "C", "D"], stored=set(), broken={"A"})
    for _ in range(3):
        sync.sync_guild_reports(_settings(sync_batch=1), raids=raids)
    assert raids.stored == {"B", "C", "D"}


def test_a_run_stops_after_twice_the_batch_in_attempts() -> None:
    raids = FakeRaids(["A", "B", "C", "D", "E"], stored=set(), broken={"A", "B", "C", "D", "E"})
    result = sync.sync_guild_reports(_settings(sync_batch=2), raids=raids)
    assert raids.analysed == ["A", "B", "C", "D"]
    assert result["imported"] == [] and result["remaining"] == 5


def test_sync_with_nothing_new_analyses_nothing() -> None:
    raids = FakeRaids(["A"], stored={"A"})
    assert sync.sync_guild_reports(_settings(), raids=raids) == {"imported": [], "failed": {}, "remaining": 0}
    assert raids.analysed == []


def test_sync_needs_a_guild_id() -> None:
    with pytest.raises(ValueError, match="TOADS_WCL_GUILD_ID"):
        sync.sync_guild_reports(_settings(wcl_guild_id=0), raids=FakeRaids([], set()))


def _ops_scenario(number: int) -> Any:
    """Bind REQ-DEV-OPS-<nnn> from dev_ops.feature (the id is built, not written out)."""
    req_id = f"REQ-DEV-OPS-{number:03d}"
    for line in (FEATURES / "dev_ops.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "dev_ops.feature"), m.group(1))
    raise LookupError(req_id)


@_ops_scenario(4)
def test_ops_004() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('the guild\'s reports on Warcraft Logs are "{codes}", newest first, and "{stored}" is stored'))
def guild_reports(ctx: dict[str, Any], codes: str, stored: str) -> None:
    ctx["raids"] = FakeRaids([c.strip() for c in codes.split(",")], stored={stored})


@given(parsers.parse('"{code}" fails to analyse'))
def broken_report(ctx: dict[str, Any], code: str) -> None:
    ctx["raids"].broken.add(code)


@when(parsers.parse("the sync runs with a batch of {batch:d}"))
def run_sync(ctx: dict[str, Any], batch: int) -> None:
    ctx["result"] = sync.sync_guild_reports(_settings(sync_batch=batch), raids=ctx["raids"])


@then(parsers.parse('"{ok}" are stored, "{bad}" is listed as failed and {left:d} report is left for the next run'))
def sync_result(ctx: dict[str, Any], ok: str, bad: str, left: int) -> None:
    result, raids = ctx["result"], ctx["raids"]
    stored = [c.strip() for c in ok.split(",")]
    assert raids.analysed == [bad, *stored]  # newest first; the next older report took the failed one's place
    assert set(stored) <= raids.stored and bad not in raids.stored
    assert result["imported"] == stored
    assert list(result["failed"]) == [bad]
    assert result["remaining"] == left


def test_raid_service_is_the_analyzers_on_the_guild_key() -> None:
    from wcl_app import RaidService

    assert isinstance(sync.raid_service(_settings()), RaidService)
