"""REQ-DEV-CI-004: the GitHub Pages preview workflow."""

from pathlib import Path
from typing import Any

import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "dev_ci.feature"


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-004 When apps/web changes on main, CI shall publish a static build of the web app with sample data "
    "to GitHub Pages, marked as a preview",
)
def test_pages_preview() -> None:
    pass


@given("the Pages workflow", target_fixture="workflow")
def workflow() -> dict[Any, Any]:
    data = yaml.safe_load((ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _steps(workflow: dict[Any, Any], job: str) -> list[dict[str, Any]]:
    steps = workflow["jobs"][job]["steps"]
    assert isinstance(steps, list)
    return steps


@then("it runs on pushes to main that change apps/web")
def runs_on_main(workflow: dict[Any, Any]) -> None:
    push = workflow[True]["push"]  # PyYAML reads the bare `on:` key as True
    assert push["branches"] == ["main"]
    assert "apps/web/**" in push["paths"]


@then("it builds apps/web with PREVIEW=1 under the Pages base path")
def builds_preview(workflow: dict[Any, Any]) -> None:
    assert workflow["jobs"]["build"]["defaults"]["run"]["working-directory"] == "apps/web"
    build = next(s for s in _steps(workflow, "build") if s.get("run") == "npm run build")
    assert build["env"]["PREVIEW"] == "1"
    assert build["env"]["BASE_PATH"] == "${{ steps.pages.outputs.base_path }}"
    upload = next(s for s in _steps(workflow, "build") if str(s.get("uses", "")).startswith("actions/upload-pages"))
    assert upload["with"]["path"] == "apps/web/build"


@then("it deploys that build to GitHub Pages")
def deploys(workflow: dict[Any, Any]) -> None:
    deploy = workflow["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["environment"]["name"] == "github-pages"
    assert any(str(s.get("uses", "")).startswith("actions/deploy-pages") for s in _steps(workflow, "deploy"))
    assert workflow["permissions"]["pages"] == "write"


@then("the web layout shows a sample-data banner in the preview build")
def banner() -> None:
    layout = (ROOT / "apps" / "web" / "src" / "routes" / "+layout.svelte").read_text(encoding="utf-8")
    assert "{#if __PREVIEW__}" in layout
    assert "Preview with sample data" in layout
