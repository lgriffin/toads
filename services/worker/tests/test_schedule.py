"""`toads-worker schedule`: the hub's derived pages rebuilt on an interval (REQ-DEV-OPS-003)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from pytest_bdd import given, scenario, then, when
from toads_worker import schedule
from toads_worker.settings import Settings

FEATURES = Path(__file__).resolve().parents[3] / "tests" / "features"


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": SecretStr("postgresql+psycopg://u:p@localhost/db"),
        "redis_url": "redis://localhost",
        "wcl_client_id": "id",
        "wcl_client_secret": SecretStr("replace-me"),
        "wcl_guild_id": 1,
        "credentials_keys": SecretStr("replace-me"),
        "raid_sheets_config": tmp_path / "missing.yaml",
    }
    values.update(overrides)
    return Settings(**values)


def test_default_jobs_refresh_the_hub_every_half_hour(tmp_path: Path) -> None:
    jobs = schedule.jobs_for(_settings(tmp_path))
    assert [(j.name, j.every_seconds) for j in jobs] == [
        ("publish-home", 1800.0),
        ("publish-performance", 1800.0),
        ("publish-badges", 1800.0),
        ("publish-reference", 1800.0),
    ]


def test_sheets_are_imported_only_when_configured(tmp_path: Path) -> None:
    config = tmp_path / "raid_sheets.yaml"
    config.write_text("spreadsheets: []\n", encoding="utf-8")
    jobs = schedule.jobs_for(_settings(tmp_path, raid_sheets_config=config, sheets_refresh_minutes=60))
    assert ("import-sheets", 3600.0) in [(j.name, j.every_seconds) for j in jobs]


def test_zero_turns_a_job_off(tmp_path: Path) -> None:
    assert schedule.jobs_for(_settings(tmp_path, hub_refresh_minutes=0)) == []
    with pytest.raises(RuntimeError, match="turned off"):
        schedule.run_forever([])


def test_jobs_run_at_start_then_each_interval_and_a_failure_does_not_stop_the_rest() -> None:
    calls: list[str] = []

    def boom() -> None:
        calls.append("boom")
        raise RuntimeError("hub down")

    jobs = [
        schedule.Job("boom", 10.0, boom),
        schedule.Job("ok", 30.0, lambda: calls.append("ok")),
    ]
    assert schedule.run_due(jobs, 0.0) == ["boom", "ok"]
    assert schedule.run_due(jobs, 5.0) == []
    assert schedule.run_due(jobs, 10.0) == ["boom"]
    assert schedule.run_due(jobs, 30.0) == ["boom", "ok"]
    assert calls == ["boom", "ok", "boom", "boom", "ok"]


def test_run_forever_sleeps_until_the_next_job_is_due() -> None:
    now = [0.0]
    slept: list[float] = []
    ran: list[str] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    jobs = [schedule.Job("a", 45.0, lambda: ran.append("a"))]
    turns = iter([True, True, True, False])
    schedule.run_forever(jobs, clock=lambda: now[0], sleep=sleep, keep_going=lambda: next(turns))
    assert ran == ["a", "a", "a"]
    assert slept == [45.0, 45.0, 45.0]


def _ops_scenario(number: int) -> Any:
    """Bind REQ-DEV-OPS-<nnn> from dev_ops.feature (the id is built, not written out)."""
    req_id = f"REQ-DEV-OPS-{number:03d}"
    for line in (FEATURES / "dev_ops.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "dev_ops.feature"), m.group(1))
    raise LookupError(req_id)


@_ops_scenario(3)
def test_ops_003() -> None:
    pass


@pytest.fixture
def ops() -> dict[str, Any]:
    return {}


@given("the scheduler with the default intervals")
def default_scheduler(tmp_path: Path, ops: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[str] = []
    hub_up = [False]

    def publisher(name: str) -> Any:
        def publish(_settings: Settings) -> dict[str, int]:
            if not hub_up[0]:
                raise ConnectionError("hub down")
            published.append(name)
            return {}

        return publish

    monkeypatch.setattr(schedule, "publish_home_page", publisher("home"))
    monkeypatch.setattr(schedule, "publish_performance", publisher("performance"))
    monkeypatch.setattr(schedule, "publish_badges", publisher("badges"))
    monkeypatch.setattr(schedule, "publish_reference_page", publisher("reference"))
    ops.update(jobs=schedule.jobs_for(_settings(tmp_path)), published=published, hub_up=hub_up)


@when("the hub is down for the first run")
def first_run_fails(ops: dict[str, Any]) -> None:
    assert schedule.run_due(ops["jobs"], 0.0) == [
        "publish-home",
        "publish-performance",
        "publish-badges",
        "publish-reference",
    ]
    assert ops["published"] == []
    ops["hub_up"][0] = True


@then("the analyzer widgets and performance numbers are published again 30 minutes later")
def published_later(ops: dict[str, Any]) -> None:
    assert schedule.run_due(ops["jobs"], 29 * 60.0) == []
    assert schedule.run_due(ops["jobs"], 30 * 60.0) == [
        "publish-home",
        "publish-performance",
        "publish-badges",
        "publish-reference",
    ]
    assert ops["published"] == ["home", "performance", "badges", "reference"]
