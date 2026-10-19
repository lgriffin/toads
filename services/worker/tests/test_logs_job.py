"""The Logs job: wcl_app.raid_pages over wcl-store, the list first, then each analysis the hub asks for."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from toads_worker.jobs import analyse, logs
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


def test_empty_storage_lists_nothing(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    index = logs.build_index(logs.build_pages(sqlite_storage), now=lambda: datetime(2026, 10, 19, 8, 0, 0))
    assert index == {"version": 1, "generated_at": "2026-10-19 08:00:00", "raids": [], "bosses": []}


def test_a_stored_raid_is_listed_with_its_weekday_and_analysis(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    pages = logs.build_pages(sqlite_storage)
    assert [p.summary.report_id for p in pages] == [CODE]
    index = logs.build_index(pages)
    (raid,) = index["raids"]
    assert raid["report_id"] == CODE
    assert raid["weekday"] in range(7)
    page = pages[0].to_dict()
    assert page["version"] == 1
    assert page["composition"]
    json.dumps(index)  # plain JSON, ready to send
    json.dumps(page)


def test_publish_sends_the_list_then_each_missing_raid(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    seen: list[tuple[str, str, str]] = []
    bodies: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers["authorization"]))
        bodies[request.url.path] = json.loads(request.content)
        if request.url.path == "/api/worker/logs":
            # A raid the worker does not hold is skipped rather than failing the run.
            return httpx.Response(200, json={"raids": 1, "missing": [CODE, "gone"]})
        return httpx.Response(200, json={"report_id": CODE})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub) == {"raids": 1, "sent": 1}
    auth = "Bearer test-service-token"
    assert seen == [("PUT", "/api/worker/logs", auth), ("PUT", f"/api/worker/logs/{CODE}", auth)]
    assert bodies[f"/api/worker/logs/{CODE}"]["page"]["summary"]["report_id"] == CODE


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        logs.publish_logs(_settings(token=""), storage=sqlite_storage)
