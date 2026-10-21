"""REQ-DEV-CI-001 and 002: scripts/dev.py holds every check, CI runs it, and `ci-success` is the one verdict."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "dev_ci.feature"
CI = ROOT / ".github" / "workflows" / "ci.yml"
GATE = "ci-success"

# The scripts/dev.py tasks each CI job runs. A job that drops or swaps a task fails `each_job_runs_its_tasks`.
JOB_TASKS = {
    "python": {"format", "lint", "imports", "reqs", "ratchet", "types", "test", "diffcov"},
    "postgres": {"postgres"},
    "backup": {"shell", "backup"},
    "security": {"security", "audit"},
    "web": {"web-check", "web-test", "web-build", "web-audit"},
    "e2e": {"e2e"},
}
# CI jobs that run no scripts/dev.py task, each with the reason a local `check` cannot run it.
OUTSIDE_DEV = {
    "images": "builds each Docker image with buildx and runs its console scripts inside it",
    GATE: "the fan-in gate over the other jobs (scripts/ci_gate.py)",
}


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"toads_{name}", ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while the class is built
    spec.loader.exec_module(module)
    return module


dev = _load("dev")
gate = _load("ci_gate")
reqs = _load("reqs")
ratchet = _load("ratchet")


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-001 When a PR is opened, CI shall run lint, types, unit, BDD, contract, security and dependency audits "
    "and block merge on any failure",
)
def test_ci_gate() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-002 If a requirement ID in this document has no scenario, or a scenario has no ID or persona tag, "
    "then the reqs job shall fail",
)
def test_reqs_gate() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-003 If coverage of the api, worker, bot and hub-db falls below the floor in pyproject.toml, a PR "
    "covers less than 90 percent of the lines it changes, or a PR lowers the floor, then CI shall fail",
)
def test_coverage_ratchet() -> None:
    pass


def _task_calls(text: str) -> set[str]:
    return {task for line in re.findall(r"scripts/dev\.py ([a-z0-9 -]+)", text) for task in line.split()}


# The one shape a step that runs tasks may take: the whole `run:` is the call, so no `|| true`, `#` or `;` can hide it.
TASK_STEP = re.compile(r"(?:uv run python|python3) (?:\.\./\.\./)?scripts/dev\.py(?: [a-z0-9-]+)+")


def _tasks_run_by(job: dict[str, Any]) -> set[str]:
    """The scripts/dev.py tasks a job's steps run (only `run:` commands, not comments or names)."""
    return {task for step in job.get("steps", []) for task in _task_calls(str(step.get("run", "")))}


def _task_step_problems(job: dict[str, Any]) -> list[str]:
    """Why a step that names scripts/dev.py might not run its tasks or fail its job when they fail."""
    problems = []
    for step in job.get("steps", []):
        run = str(step.get("run", ""))
        if "scripts/dev.py" not in run:
            continue
        if not TASK_STEP.fullmatch(run.strip()):
            problems.append(f"not a plain task call: {run.strip()!r}")
        if "if" in step:
            problems.append(f"can be skipped: {run.strip()!r}")
        if step.get("continue-on-error"):
            problems.append(f"cannot fail its job: {run.strip()!r}")
    return problems


@given("the CI workflow", target_fixture="workflow")
def workflow() -> dict[Any, Any]:
    data = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@then("it runs on every pull request and on pushes to main")
def triggers(workflow: dict[Any, Any]) -> None:
    on = workflow[True]  # PyYAML reads the bare `on:` key as True
    assert "pull_request" in on
    assert on["pull_request"] is None  # no branch or path filter: every PR runs every job
    assert on["push"]["branches"] == ["main"]


@then("every check that needs no network or services runs locally as scripts/dev.py check")
def check_covers_ci(workflow: dict[Any, Any]) -> None:
    assert set(dev.CHECK) <= set(dev.TASKS)
    run = set().union(*(_tasks_run_by(job) for job in workflow["jobs"].values()))
    assert set(dev.CHECK) <= run, "a task in `check` is not run by any CI job"
    assert run <= set(dev.TASKS), "CI names a task scripts/dev.py does not have"
    recipes = [line for line in (ROOT / "justfile").read_text(encoding="utf-8").splitlines() if line.startswith(" ")]
    assert _task_calls("\n".join(recipes)) <= {"check", "fix", *dev.TASKS}


@then("each CI job runs exactly its scripts/dev.py tasks")
def each_job_runs_its_tasks(workflow: dict[Any, Any]) -> None:
    run = {name: _tasks_run_by(job) for name, job in workflow["jobs"].items()}
    assert {name: tasks for name, tasks in run.items() if tasks} == JOB_TASKS
    assert [problem for job in workflow["jobs"].values() for problem in _task_step_problems(job)] == []
    assert {name for name, tasks in run.items() if not tasks} == set(OUTSIDE_DEV)


@then("the ci-success job needs every other job and is the only job that can be skipped")
def gate_needs_everything(workflow: dict[Any, Any]) -> None:
    jobs = workflow["jobs"]
    assert set(jobs[GATE]["needs"]) == set(jobs) - {GATE}
    # A job-level `if:` can skip a job, and the gate counts skipped as failed; only the gate itself may have one.
    assert {name for name, job in jobs.items() if "if" in job} == {GATE}
    assert jobs[GATE]["if"] == "always()"


def _needs(**results: str) -> dict[str, str]:
    return {"NEEDS_JSON": json.dumps({job: {"result": result} for job, result in results.items()})}


@then("ci-success fails when any job it needs failed, was cancelled or was skipped")
def gate_verdict() -> None:
    assert gate.main(_needs(python="success", web="success")) == 0
    for bad in ("failure", "cancelled", "skipped"):
        assert gate.main(_needs(python="success", web=bad)) == 1
    assert gate.main({}) == 1
    assert gate.main({"NEEDS_JSON": "not json"}) == 1
    assert gate.main({"NEEDS_JSON": "{}"}) == 1
    assert gate.failures({"python": {}}) == {"python": "missing"}


@given("a feature file", target_fixture="features")
def features(tmp_path: Path) -> Path:
    return tmp_path


def _errors(features: Path, body: str) -> list[str]:
    for old in features.glob("*.feature"):
        old.unlink()
    (features / "x.feature").write_text(f"Feature: x\n{body}", encoding="utf-8")
    return list(reqs.parse(features)[1])


@then("a scenario without a REQ id fails the reqs check")
def no_id(features: Path) -> None:
    assert _errors(features, "  @ears_ubiquitous @member\n  Scenario: The hub shall do a thing\n")
    assert not _errors(features, "  @ears_ubiquitous @member\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n")


@then("a scenario without exactly one EARS tag fails the reqs check")
def ears_tag(features: Path) -> None:
    assert _errors(features, "  @member\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n")
    two = "  @ears_ubiquitous @ears_optional @member\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n"
    assert _errors(features, two)


@then("a scenario without a persona tag fails the reqs check")
def persona_tag(features: Path) -> None:
    assert _errors(features, "  @ears_ubiquitous\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n")


@then("a duplicated REQ id fails the reqs check")
def duplicate_id(features: Path) -> None:
    one = "  @ears_ubiquitous @member\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n"
    assert any("duplicate" in error for error in _errors(features, one * 2))


@then("CI runs the reqs check")
def ci_runs_reqs() -> None:
    data = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert "reqs" in _tasks_run_by(data["jobs"]["python"])
    assert "reqs" in dev.CHECK
    assert dev.TASKS["reqs"].steps[0].command == ["python", "scripts/reqs.py", "--check"]


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(SystemExit):
        dev.main(["no-such-task"])


def test_fix_must_run_alone() -> None:
    with pytest.raises(SystemExit):
        dev.main(["fix", "lint"])


def _failing_runs(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    ran: list[object] = []

    def fail(task: object) -> bool:
        ran.append(task)
        return False

    monkeypatch.setattr(dev, "_run", fail)
    return ran


def test_stops_at_the_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    ran = _failing_runs(monkeypatch)
    assert dev.run_tasks(["lint", "types"], keep_going=False) == 1
    assert len(ran) == 1


def test_keep_going_runs_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    ran = _failing_runs(monkeypatch)
    assert dev.run_tasks(["lint", "types"], keep_going=True) == 1
    assert len(ran) == 2


def test_the_parser_reads_run_steps_only() -> None:
    """A quoted job id is a job, and only a `run:` step names a task (not a step's name)."""
    data = yaml.safe_load(
        'jobs:\n  "release-check":\n    steps:\n      - run: python scripts/dev.py lint\n'
        "      - name: python scripts/dev.py types\n"
    )
    assert _tasks_run_by(data["jobs"]["release-check"]) == {"lint"}


@pytest.mark.parametrize(
    ("step", "problem"),
    [
        ("run: python3 scripts/dev.py lint || true", "not a plain task call"),
        ("run: '# python3 scripts/dev.py lint'", "not a plain task call"),
        ("run: python3 scripts/dev.py lint; exit 0", "not a plain task call"),
        ("run: python3 scripts/dev.py lint\n        if: false", "can be skipped"),
        ("run: python3 scripts/dev.py lint\n        continue-on-error: true", "cannot fail its job"),
    ],
)
def test_a_task_step_that_could_hide_its_result_is_refused(step: str, problem: str) -> None:
    job = yaml.safe_load(f"steps:\n      - {step}\n")
    assert any(found.startswith(problem) for found in _task_step_problems(job))


def test_plain_task_steps_pass() -> None:
    job = yaml.safe_load(
        "steps:\n  - run: uv run python scripts/dev.py format lint\n  - run: python3 ../../scripts/dev.py e2e\n"
    )
    assert _task_step_problems(job) == []


@then("the test task measures the api, worker, bot and hub-db against the floor in pyproject.toml")
def coverage_floor() -> None:
    (step,) = dev.TASKS["test"].steps
    assert {"--cov=toads_api", "--cov=toads_worker", "--cov=toads_bot", "--cov=hub_db"} <= set(step.command)
    assert not any(arg.startswith("--cov-fail-under") for arg in step.command)  # the floor lives in pyproject.toml
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 96


@then("CI checks the coverage of the lines a PR changes against main")
def diff_coverage(workflow: dict[Any, Any]) -> None:
    (step,) = dev.TASKS["diffcov"].steps
    assert "--compare-branch=origin/main" in step.command
    assert "--fail-under=90" in step.command
    python = workflow["jobs"]["python"]
    run = [
        task
        for step in python["steps"]
        for line in re.findall(r"scripts/dev\.py ([a-z0-9 -]+)", str(step.get("run", "")))
        for task in line.split()
    ]
    assert run.index("test") < run.index("diffcov"), "diffcov reads the coverage.xml that test writes"
    assert python["steps"][0]["with"]["fetch-depth"] == 0


@then("a floor that goes down or disappears fails the ratchet, and one that rises passes")
def ratchet_is_one_way() -> None:
    def config(value: float | None) -> dict[str, Any]:
        return {} if value is None else {"tool": {"coverage": {"report": {"fail_under": value}}}}

    assert ratchet.lowered(config(96), config(95)) == ["tool.coverage.report.fail_under went down from 96 to 95"]
    assert ratchet.lowered(config(96), config(None)) == ["tool.coverage.report.fail_under was 96 and is gone"]
    assert ratchet.lowered(config(96), config(96)) == []
    assert ratchet.lowered(config(96), config(97)) == []
    assert ratchet.lowered(config(None), config(80)) == []  # a new floor


@then("CI runs the ratchet against main")
def ci_runs_ratchet(workflow: dict[Any, Any]) -> None:
    assert "ratchet" in _tasks_run_by(workflow["jobs"]["python"])
    assert "ratchet" in dev.CHECK
