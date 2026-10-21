"""REQ-DEV-CI-008: taking each analyzer release through a PR that merges itself once CI passes."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location("analyzer_release", ROOT / "scripts" / "analyzer_release.py")
assert _spec and _spec.loader
analyzer_release = importlib.util.module_from_spec(_spec)
sys.modules["analyzer_release"] = analyzer_release
_spec.loader.exec_module(analyzer_release)

SOURCES = "".join(
    f'wcl-{name} = {{ git = "https://github.com/lgriffin/warcraftlogs_project", '
    f'subdirectory = "packages/wcl-{name}", rev = "abc" }}\n'
    for name in ("core", "store", "app")
)
TOKEN = "${{ secrets.ANALYZER_BUMP_TOKEN }}"  # noqa: S105 - a workflow expression, not a secret


@scenario(
    str(ROOT / "tests" / "features" / "dev_ci.feature"),
    "REQ-DEV-CI-008 When lgriffin/warcraftlogs_project publishes a newer release, the analyzer release workflow shall "
    "open a PR pinning wcl-core, wcl-store and wcl-app to that release and merge it once CI passes on it",
)
def test_analyzer_release_workflow() -> None:
    pass


@given("the analyzer release workflow", target_fixture="workflow")
def workflow() -> dict[Any, Any]:
    data = yaml.safe_load((ROOT / ".github" / "workflows" / "analyzer-release.yml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@then("it looks for a release nightly, or by hand, while ANALYZER_RELEASES_ENABLED is true")
def triggers(workflow: dict[Any, Any]) -> None:
    on = workflow[True]  # PyYAML reads the bare `on:` key as True
    assert len(on["schedule"]) == 1
    assert "workflow_dispatch" in on
    assert on["workflow_run"] == {"workflows": ["CI"], "types": ["completed"], "branches": ["analyzer/**"]}
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert "vars.ANALYZER_RELEASES_ENABLED == 'true'" in job["if"]
        assert job["env"]["GH_TOKEN"] == TOKEN


@then("it pins all three analyzer packages to the latest plain release and never steps back")
def bump(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["bump"]
    run = job["steps"][-1]["run"]
    assert "releases/latest" in run
    assert "compare/$pinned...$latest" in run
    assert 'python3 scripts/analyzer_release.py pin "$latest"' in run
    assert "uv lock" in run
    assert "${{" not in run
    assert job["steps"][0]["with"]["token"] == TOKEN


@then("it merges only a green analyzer PR that changes nothing but the pin")
def merge(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["merge"]
    assert "github.event.workflow_run.conclusion == 'success'" in job["if"]
    assert "github.event.workflow_run.event == 'pull_request'" in job["if"]
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in job["if"]
    check, merge_step = job["steps"][-2:]
    assert check["id"] == "check"
    assert '"pyproject.toml uv.lock "' in check["run"]
    assert 'python3 scripts/analyzer_release.py pin "$tag"' in check["run"]
    assert "git diff --quiet HEAD -- pyproject.toml uv.lock" in check["run"]
    assert merge_step["if"] == "steps.check.outputs.pin-only == 'true'"
    assert '--match-head-commit "$SHA"' in merge_step["run"]
    assert job["steps"][0]["with"]["persist-credentials"] is False
    for step in job["steps"]:
        assert "${{" not in step.get("run", "")


def test_current_reads_the_shared_pin() -> None:
    assert analyzer_release.current(SOURCES) == "abc"


def test_current_refuses_packages_on_different_pins() -> None:
    with pytest.raises(ValueError, match="different versions"):
        analyzer_release.current(SOURCES.replace('wcl-app", rev = "abc"', 'wcl-app", rev = "def"'))


def test_pin_moves_every_package_to_the_release_tag() -> None:
    pinned = analyzer_release.pin(SOURCES, "v4.5.0")
    assert pinned.count('tag = "v4.5.0"') == 3
    assert "rev =" not in pinned
    assert analyzer_release.current(pinned) == "v4.5.0"
    assert analyzer_release.current(analyzer_release.pin(pinned, "v4.6.0")) == "v4.6.0"


@pytest.mark.parametrize("tag", ["v4.6.0-rc1", "4.5.0", "main", 'v4.5.0" }', "v4.5.0\n"])
def test_pin_takes_only_plain_release_tags(tag: str) -> None:
    with pytest.raises(ValueError, match="not a release tag"):
        analyzer_release.pin(SOURCES, tag)


def test_the_repository_pins_all_three_packages_together() -> None:
    analyzer_release.current((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
