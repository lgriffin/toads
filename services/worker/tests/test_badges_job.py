"""The badges job: wcl_app.badges over wcl-store, published to the hub API with the service token."""

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
from toads_worker.jobs import analyse, badges
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


def test_empty_storage_publishes_nobody(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    page = badges.build_page(sqlite_storage, now=lambda: datetime(2026, 9, 28, 8, 0, 0))
    assert page == {"version": 1, "generated_at": "2026-09-28 08:00:00", "players": []}


def test_every_raider_gets_every_badge(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    page = badges.build_page(sqlite_storage)
    assert page["players"]
    ids = [b["id"] for b in page["players"][0]["badges"]]
    assert "attendance" in ids
    for p in page["players"]:
        assert [b["id"] for b in p["badges"]] == ids
        assert p["score"] == sum(b["tier"] for b in p["badges"])
    json.dumps(page)  # plain JSON, ready to send


def test_publish_puts_the_page_with_the_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path, auth=request.headers["authorization"])
        return httpx.Response(200, json={"players": 0})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert badges.publish_badges(_settings(), storage=sqlite_storage, hub=hub) == {"players": 0}
    assert seen == {"method": "PUT", "path": "/api/worker/badges", "auth": "Bearer test-service-token"}


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        badges.publish_badges(_settings(token=""), storage=sqlite_storage)
