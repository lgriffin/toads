"""The analyzer home page job: wcl_app.home over wcl-store, published to the hub API with the service token."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from toads_worker.jobs import analyse, home
from toads_worker.settings import Settings
from wcl_store.sqlite import PerformanceDB

# The analysis job's Warcraft Logs double, loaded by path (tests run with --import-mode=importlib).
_spec = importlib.util.spec_from_file_location("worker_test_analyse", Path(__file__).with_name("test_analyse.py"))
assert _spec and _spec.loader
_analyse_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyse_tests)
CODE: str = _analyse_tests.CODE
fake_wcl_client = _analyse_tests.fake_wcl_client


@pytest.fixture
def sqlite_storage(tmp_path: Path) -> Callable[[], PerformanceDB]:
    path = str(tmp_path / "analyzer.db")
    with PerformanceDB(path) as db:
        db.initialize()
    return lambda: PerformanceDB(path)


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


def test_page_has_the_hub_widgets_in_the_contract_shape(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    page = home.build_page(sqlite_storage)
    assert page["version"] == 1
    assert [w["id"] for w in page["widgets"]] == list(home.HUB_WIDGETS)
    last = next(w for w in page["widgets"] if w["id"] == "last_raid")
    assert last["kind"] == "stats" and last["tiles"] and not last["error"]
    json.dumps(page)  # plain JSON, ready to send


def test_empty_storage_still_builds_every_widget(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    page = home.build_page(sqlite_storage)
    assert [w["id"] for w in page["widgets"]] == list(home.HUB_WIDGETS)


def test_publish_puts_the_page_with_the_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path, auth=request.headers["authorization"])
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"widgets": len(seen["body"]["widgets"])})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    answer = home.publish_home_page(_settings(), storage=sqlite_storage, hub=hub)
    assert (seen["method"], seen["path"]) == ("PUT", "/api/worker/home-page")
    assert seen["auth"] == "Bearer test-service-token"
    assert answer == {"widgets": len(home.HUB_WIDGETS)}


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        home.publish_home_page(_settings(token=""), storage=sqlite_storage)


def test_weekly_healing_charts_are_built_and_measured_against_the_target(
    sqlite_storage: Callable[[], PerformanceDB],
) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    page = home.build_page(sqlite_storage, healing_target=1.0)
    widgets = {w["id"]: w for w in page["widgets"]}
    for wid in ("healing_weekly", "healers_weekly"):
        assert widgets[wid]["kind"] == "chart" and not widgets[wid]["error"], wid
        assert widgets[wid]["chart"]["version"] == 1
    chart = widgets["healing_weekly"]["chart"]
    assert len(chart["categories"]) == 12 and len(chart["series"]) <= 8
    if not chart["empty"]:  # the sample report is weeks old, so it may fall outside the window
        assert "target" in [r["key"] for r in chart["references"]]


def test_the_healing_target_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOADS_HEALING_TARGET_PER_RAID", raising=False)
    assert _settings().healing_target_per_raid is None
    monkeypatch.setenv("TOADS_HEALING_TARGET_PER_RAID", "4000000")
    assert _settings().healing_target_per_raid == 4_000_000
