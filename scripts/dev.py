"""One entry point for every check CI runs, so a local run and CI run the same commands (REQ-DEV-CI-001).

    uv run python scripts/dev.py check      # every CI check that needs no network or services, fastest first
    uv run python scripts/dev.py fix        # apply Ruff's fixes and formatting
    uv run python scripts/dev.py <task>...  # any tasks below, in order; -k keeps going after a failure

CI, the justfile and a local run all call these tasks, so each command is written once. `tests/step_defs/
test_dev_gates.py` parses `.github/workflows/ci.yml` and fails if a job stops running its tasks: a new CI job goes in
its `JOB_TASKS` or `OUTSIDE_DEV`. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = "apps/web"

# The typed Python sources (mypy strict) and the packages coverage measures. The floor is in pyproject.toml.
SOURCES = ["packages/hub-db/src", "services/api/src", "services/worker/src", "services/bot/src"]
COVERAGE = ["--cov=toads_api", "--cov=toads_worker", "--cov=toads_bot", "--cov=hub_db"]
# The community repository and the hub-db migrations, run against the Postgres in TOADS_TEST_DATABASE_URL.
POSTGRES_TESTS = ["services/api/tests/test_community_sql.py", "services/api/tests/test_community.py", "-k", "sql"]
SHELL_SCRIPTS = [
    "scripts/backup.sh",
    "scripts/backup-lib.sh",
    "scripts/restore.sh",
    "scripts/backup-install.sh",
    "tests/backup/drill.sh",
]


@dataclass(frozen=True)
class Step:
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    label: str
    steps: list[Step]
    cwd: str = "."


def task(label: str, *commands: list[str], cwd: str = ".", env: dict[str, str] | None = None) -> Task:
    return Task(label, [Step(command, env or {}) for command in commands], cwd)


# uv exports the lock without the workspace's own packages (they are not on PyPI) for pip-audit to read.
PIP_AUDIT = 'req=$(mktemp) && uv export --frozen --no-hashes --no-emit-workspace > "$req" && pip-audit -r "$req"'

TASKS: dict[str, Task] = {
    "format": task("Ruff format check", ["ruff", "format", "--check", "."]),
    "lint": task("Ruff lint and security rules", ["ruff", "check", "."]),
    "imports": task("import-linter layer contracts", ["lint-imports"]),
    "types": task("mypy strict", ["mypy", *SOURCES]),
    "reqs": task(
        "requirements traceability (docs/requirements.md is current)", ["python", "scripts/reqs.py", "--check"]
    ),
    "security": task("security-marked tests", ["pytest", "-m", "security", "-q", "--tb=short"]),
    "test": task(
        "unit and BDD tests with the coverage floor",
        ["pytest", "-n", "auto", "-q", "--tb=short", "-rs", *COVERAGE, "--cov-report=term-missing:skip-covered"],
    ),
    "postgres": task(
        "community repository and migrations on Postgres (needs TOADS_TEST_DATABASE_URL)",
        ["pytest", "-q", "--tb=short", "-rs", *POSTGRES_TESTS],
    ),
    "shell": task("shellcheck the backup scripts", ["shellcheck", "-x", *SHELL_SCRIPTS]),
    "backup": task(
        "backup and restore drill (needs Docker)",
        ["pytest", "-q", "-rs", "tests/step_defs/test_dev_backup.py"],
        env={"TOADS_BACKUP_DRILL": "1"},
    ),
    "audit": task("pip-audit the locked Python dependencies (needs network)", ["sh", "-c", PIP_AUDIT]),
    "web-check": task("svelte-check", ["npm", "run", "check"], cwd=WEB),
    "web-test": task("vitest", ["npm", "test"], cwd=WEB),
    # The second build is the GitHub Pages preview (REQ-DEV-CI-004).
    "web-build": Task(
        "web build, and the Pages preview build",
        [Step(["npm", "run", "build"]), Step(["npm", "run", "build"], {"PREVIEW": "1", "BASE_PATH": "/toads"})],
        cwd=WEB,
    ),
    "web-audit": task("npm audit (needs network)", ["npm", "audit", "--audit-level=high", "--omit=dev"], cwd=WEB),
    "e2e": task("Playwright end-to-end tests", ["npm", "run", "e2e"], cwd=WEB),
}

# What `check` runs: every CI check that needs no network, Docker or database, cheapest first so it fails fast.
CHECK = ["format", "lint", "imports", "reqs", "types", "security", "test", "web-check", "web-test"]

FIX = task("Ruff fixes and formatting", ["ruff", "check", "--fix", "."], ["ruff", "format", "."])


def _run(task: Task) -> bool:
    for step in task.steps:
        if shutil.which(step.command[0]) is None:
            print(f"  {step.command[0]} is not installed; run: just setup", file=sys.stderr)
            return False
        env = {**os.environ, **step.env} if step.env else None
        if subprocess.run(step.command, cwd=ROOT / task.cwd, env=env, check=False).returncode != 0:  # noqa: S603
            return False
    return True


def run_tasks(names: list[str], keep_going: bool) -> int:
    failed = []
    for name in names:
        print(f"\n==> {name}: {TASKS[name].label}", flush=True)
        started = time.monotonic()
        ok = _run(TASKS[name])
        print(f"<== {name}: {'ok' if ok else 'FAILED'} ({time.monotonic() - started:.1f}s)", flush=True)
        if not ok:
            failed.append(name)
            if not keep_going:
                break
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\nAll passed: {', '.join(names)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", metavar="task", help=f"check, fix, or any of: {', '.join(TASKS)}")
    parser.add_argument("-k", "--keep-going", action="store_true", help="run every task even after one fails")
    args = parser.parse_args(argv)

    tasks = args.tasks or ["check"]
    unknown = sorted(set(tasks) - {"check", "fix", *TASKS})
    if unknown:
        parser.error(f"unknown task: {', '.join(unknown)}")
    if tasks == ["fix"]:
        return 0 if _run(FIX) else 1
    names = [name for task in tasks for name in (CHECK if task == "check" else [task])]
    if "fix" in names:
        parser.error("run fix on its own")
    return run_tasks(names, args.keep_going)


if __name__ == "__main__":
    sys.exit(main())
