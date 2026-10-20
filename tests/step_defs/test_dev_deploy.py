"""REQ-DEV-CI-007 and REQ-DEV-REL-002: deploying main to the production server (docs/deploy.md)."""

from pathlib import Path
from typing import Any

import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")


@scenario(
    str(ROOT / "tests" / "features" / "dev_ci.feature"),
    "REQ-DEV-CI-007 When CI passes on a push to main and deployment is enabled, the deploy workflow shall roll that "
    "commit out to the production server over SSH, one deploy at a time",
)
def test_deploy_workflow() -> None:
    pass


@scenario(
    str(ROOT / "tests" / "features" / "dev_rel.feature"),
    "REQ-DEV-REL-002 If a migration fails during deploy, then no new API or worker container shall start serving",
)
def test_migrations_gate_deploy() -> None:
    pass


def _yaml(relative: str) -> dict[Any, Any]:
    data = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@given("the deploy workflow", target_fixture="workflow")
def workflow() -> dict[Any, Any]:
    return _yaml(".github/workflows/deploy.yml")


@then("it runs after CI completes on main, or by hand")
def triggers(workflow: dict[Any, Any]) -> None:
    on = workflow[True]  # PyYAML reads the bare `on:` key as True
    assert on["workflow_run"] == {"workflows": ["CI"], "types": ["completed"], "branches": ["main"]}
    assert "workflow_dispatch" in on
    assert workflow["concurrency"] == {"group": "deploy-production", "cancel-in-progress": False}
    assert workflow["permissions"] == {"contents": "read"}


@then("it deploys only a successful push build while DEPLOY_ENABLED is true")
def guarded(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["deploy"]
    assert "vars.DEPLOY_ENABLED == 'true'" in job["if"]
    assert "github.event.workflow_run.conclusion == 'success'" in job["if"]
    assert "github.event.workflow_run.event == 'push'" in job["if"]
    assert job["environment"] == "production"


@then("it sends only the commit sha over SSH with a pinned host key")
def ssh_step(workflow: dict[Any, Any]) -> None:
    (step,) = workflow["jobs"]["deploy"]["steps"]
    assert "github.event.workflow_run.head_sha" in step["env"]["SHA"]
    assert "-o StrictHostKeyChecking=yes" in step["run"]
    assert step["run"].rstrip().endswith('"$DEPLOY_USER@$DEPLOY_HOST" "$SHA"')
    # Secrets reach the shell through env only, never interpolated into the script.
    assert "${{" not in step["run"]


@then("the deploy script accepts only a commit on main and takes a lock")
def script_checks() -> None:
    assert "^[0-9a-f]{40}$" in DEPLOY_SCRIPT
    assert 'git merge-base --is-ancestor "$target" origin/main' in DEPLOY_SCRIPT
    assert "flock -n 9" in DEPLOY_SCRIPT
    # The checkout rewrites the script while it runs, so bash must have parsed all of it first.
    assert DEPLOY_SCRIPT.rstrip().endswith('main "$@"\nexit')


@given("the production compose file", target_fixture="compose")
def compose() -> dict[Any, Any]:
    return _yaml("infra/docker-compose.prod.yml")


@then("the API, worker and scheduler start only after both migrations complete successfully")
def gated_on_migrations(compose: dict[Any, Any]) -> None:
    for name in ("api", "worker", "scheduler"):
        depends = compose["services"][name]["depends_on"]
        for migration in ("migrate", "analyser-migrate"):
            assert depends[migration] == {"condition": "service_completed_successfully"}, (name, migration)


@then("the deploy script runs both migrations before it replaces any running container")
def migrations_first() -> None:
    up = DEPLOY_SCRIPT.index("up -d")
    assert DEPLOY_SCRIPT.index("run --rm migrate") < up
    assert DEPLOY_SCRIPT.index("run --rm analyser-migrate") < up
    # config/ is read only at startup, so every service that mounts it restarts even when its image did not change.
    readers = [
        n
        for n, s in _yaml("infra/docker-compose.prod.yml")["services"].items()
        if "../config:/config:ro,z" in [v for v in s.get("volumes", []) if isinstance(v, str)]
    ]
    assert DEPLOY_SCRIPT.index(f"restart {' '.join(readers)}") > up
