"""REQ-DEV-CI-004 to 006: the GitHub Pages preview workflow and its pretend sign-in."""

from pathlib import Path
from typing import Any

import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "dev_ci.feature"
WEB = ROOT / "apps" / "web" / "src"


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-004 When apps/web changes on main, CI shall publish a static build of the web app with sample data "
    "to GitHub Pages, marked as a preview",
)
def test_pages_preview() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-005 Where the web app is built as the Pages preview, it shall open signed out on the public landing "
    "page and offer a pretend sign-in as a raider or an officer",
)
def test_preview_sign_in() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-DEV-CI-006 Where the web app is built as the Pages preview, it shall also offer a pretend sign-in as a super "
    "admin, and only that view shall manage bank grants and officer tokens",
)
def test_preview_super_admin() -> None:
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


def _read(relative: str) -> str:
    return (WEB / relative).read_text(encoding="utf-8")


@given("the preview's pretend sign-in", target_fixture="login")
def login() -> str:
    page = _read("routes/login/+page.svelte")
    # Only the preview build serves /login; the real site signs in with Discord at /auth/login.
    assert "if (!__PREVIEW__) error(404" in _read("routes/login/+page.ts")
    return page


@then("the landing page sends a signed-out visitor to it")
def landing_links_login() -> None:
    landing = _read("routes/+page.svelte")
    assert "previewSession.role ? 'Hopscotch' : null" in landing
    assert "`${base}/login/`" in landing


@then("it offers the raider and the officer view")
def offers_both_views(login: str) -> None:
    assert "role: 'member'" in login
    assert "role: 'officer'" in login
    layout = _read("routes/+layout.svelte")
    assert "Switch to officer view" in layout
    assert "Log out" in layout


@then("the preview asks a signed-out visitor to sign in for member pages and keeps raiders out of the officer console")
def gates_pages() -> None:
    gate = _read("lib/preview/gate.ts")
    assert "if (role === null) return 'sign-in';" in gate
    assert "under(p, '/officers') && !hasOfficerPowers(role)" in gate
    assert "previewGate(path, previewSession.role)" in _read("routes/+layout.svelte")


@then("it offers the super admin view")
def offers_super_admin(login: str) -> None:
    assert "role: 'admin'" in login
    assert "Sign in as a super admin" in login
    assert "'member' | 'officer' | 'admin'" in _read("lib/preview/gate.ts")


@then("only the super admin view manages bank grants and officer tokens in the preview bank")
def admin_manages_grants() -> None:
    bank = _read("lib/preview/bank-fake.ts")
    assert "const admin = () => previewSession.role === 'admin';" in bank
    assert bank.count("if (!admin()) return refuse(403, 'Super admins only.');") == 2
