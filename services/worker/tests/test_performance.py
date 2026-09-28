"""The "Your performance" job: each raider's number against the guild median for the same role, published to the hub."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from toads_worker.jobs import analyse, performance
from toads_worker.settings import Settings
from wcl_core.models import (
    DPSPerformance,
    HealerPerformance,
    RaidAnalysis,
    RaidComposition,
    RaidMetadata,
    TankPerformance,
)
from wcl_store.sqlite import PerformanceDB

# The analysis job's Warcraft Logs double, loaded by path (tests run with --import-mode=importlib).
_spec = importlib.util.spec_from_file_location("worker_perf_analyse", Path(__file__).with_name("test_analyse.py"))
assert _spec and _spec.loader
_analyse_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyse_tests)
CODE: str = _analyse_tests.CODE
fake_wcl_client = _analyse_tests.fake_wcl_client


def _raid(
    code: str, healers: dict[str, int], dps: dict[str, int], tanks: dict[str, float] | None = None
) -> RaidAnalysis:
    return RaidAnalysis(
        metadata=RaidMetadata(report_id=code, title=f"Raid {code}", owner="toad", start_time=0),
        composition=RaidComposition(),
        healers=[HealerPerformance(n, "Priest", i, total_healing=v) for i, (n, v) in enumerate(healers.items())],
        tanks=[
            TankPerformance(n, "Warrior", 50 + i, mitigation_percent=v)
            for i, (n, v) in enumerate((tanks or {}).items())
        ],
        dps=[DPSPerformance(n, "Rogue", 100 + i, "melee", total_damage=v) for i, (n, v) in enumerate(dps.items())],
    )


def _listed(code: str, date: str) -> dict[str, Any]:
    return {"report_id": code, "title": f"Karazhan {date}", "raid_date": f"{date} 20:00:00"}


def test_median_is_over_the_same_role_only() -> None:
    board = performance.standings(_raid("a", {"Lily": 900, "Pad": 500, "Moss": 100}, {"Croak": 5_000_000}))
    lily = board["lily"]
    assert (lily.median, lily.rank, lily.of) == (500.0, 1, 3)
    # One rogue: the damage dealers' median is theirs alone, never the healers'.
    assert (board["croak"].median, board["croak"].rank, board["croak"].of) == (5_000_000.0, 1, 1)


def test_a_name_in_two_roles_keeps_its_first() -> None:
    board = performance.standings(_raid("a", {"Swap": 10}, {"Swap": 20}, tanks={"Swap": 55.0}))
    assert board["swap"].score.role == "tank"


def test_page_has_the_last_raid_and_each_players_recent_raids_in_that_role() -> None:
    older = _raid("old", {"Lily": 400, "Pad": 600}, {"Croak": 100})
    newer = _raid("new", {"Lily": 900, "Pad": 500}, {"Croak": 300, "Ribbit": 200})
    page = performance.page_from(
        [(_listed("new", "2026-09-23"), newer), (_listed("old", "2026-09-16"), older)], "2026-09-24 08:00:00"
    )
    assert page["version"] == performance.PAGE_VERSION
    assert page["raid"] == {"report_id": "new", "title": "Karazhan 2026-09-23", "date": "2026-09-23"}
    lily = next(p for p in page["players"] if p["name"] == "Lily")
    assert lily | {"recent": None} == {
        "name": "Lily",
        "class": "Priest",
        "role": "healer",
        "metric": "Healing",
        "unit": "amount",
        "value": 900,
        "median": 700.0,
        "rank": 1,
        "of": 2,
        "recent": None,
    }
    # Oldest first, each against that raid's healer median.
    assert lily["recent"] == [
        {"date": "2026-09-16", "value": 400, "median": 500.0},
        {"date": "2026-09-23", "value": 900, "median": 700.0},
    ]
    ribbit = next(p for p in page["players"] if p["name"] == "Ribbit")
    assert [r["date"] for r in ribbit["recent"]] == ["2026-09-23"]
    json.dumps(page)


def test_no_raids_gives_an_empty_page() -> None:
    page = performance.page_from([], "2026-09-24 08:00:00")
    assert (page["raid"], page["players"]) == (None, [])


@pytest.fixture
def sqlite_storage(tmp_path: Path) -> Callable[[], PerformanceDB]:
    path = str(tmp_path / "analyzer.db")
    with PerformanceDB(path) as db:
        db.initialize()
    return lambda: PerformanceDB(path)


def test_build_page_reads_stored_raids(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    assert performance.build_page(sqlite_storage)["raid"] is None
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    page = performance.build_page(sqlite_storage)
    assert page["raid"]["report_id"] == CODE
    assert page["players"]
    for p in page["players"]:
        assert p["role"] in performance.METRICS
        assert p["recent"][-1]["value"] == p["value"]


def _settings(token: str = "test-service-token") -> Settings:  # noqa: S107
    return Settings(
        database_url=SecretStr("postgresql+psycopg://u:p@localhost/db"),
        redis_url="redis://localhost",
        wcl_client_id="id",
        wcl_client_secret=SecretStr("replace-me"),
        wcl_guild_id=1,
        credentials_keys=SecretStr("replace-me"),
        hub_api_url="http://hub.test",
        hub_service_token=SecretStr(token),
    )


def test_publish_puts_the_page_with_the_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path, auth=request.headers["authorization"])
        return httpx.Response(200, json={"players": 0})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert performance.publish_performance(_settings(), storage=sqlite_storage, hub=hub) == {"players": 0}
    assert seen == {"method": "PUT", "path": "/api/worker/performance", "auth": "Bearer test-service-token"}


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        performance.publish_performance(_settings(token=""), storage=sqlite_storage)
