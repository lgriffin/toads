"""The character pages job: wcl_app.character_pages over wcl-store, for the names the hub asks for."""

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
from toads_worker.jobs import analyse, characters
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


def _raider(storage: Callable[[], PerformanceDB]) -> str:
    with storage() as db:
        roster = db.get_raid_analysis(CODE)
    assert roster is not None
    return roster.healers[0].name


def test_no_raids_no_pages(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    page = characters.build_pages(sqlite_storage, ["Hopscotch"], now=lambda: datetime(2026, 10, 16, 8, 0, 0))
    assert page == {"version": 1, "generated_at": "2026-10-16 08:00:00", "pages": []}


def test_a_page_for_each_named_raider_once(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    name = _raider(sqlite_storage)
    page = characters.build_pages(sqlite_storage, [name, name.upper(), "Nobody"])
    (built,) = page["pages"]
    assert built["name"] == name and built["recent"][0]["role"] == "healer"
    json.dumps(page)  # plain JSON, ready to send


def test_publish_asks_for_names_then_puts_the_pages(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    name = _raider(sqlite_storage)
    seen: list[tuple[str, str, str]] = []
    sent: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers["authorization"]))
        if request.method == "GET":
            return httpx.Response(200, json={"names": [name, "Nobody"]})
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"pages": len(sent["pages"])})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert characters.publish_character_pages(_settings(), storage=sqlite_storage, hub=hub) == {"pages": 1}
    auth = "Bearer test-service-token"
    assert seen == [
        ("GET", "/api/worker/character-pages/wanted", auth),
        ("PUT", "/api/worker/character-pages", auth),
    ]
    assert [p["name"] for p in sent["pages"]] == [name]


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        characters.publish_character_pages(_settings(token=""), storage=sqlite_storage)
