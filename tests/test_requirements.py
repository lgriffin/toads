"""The feature files are the spec: every scenario is traceable and docs/requirements.md is current."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("reqs", Path(__file__).parent.parent / "scripts" / "reqs.py")
assert _spec and _spec.loader
reqs = importlib.util.module_from_spec(_spec)
sys.modules["reqs"] = reqs
_spec.loader.exec_module(reqs)

pytestmark = pytest.mark.maintainer


def test_every_scenario_is_traceable() -> None:
    found, errors = reqs.parse()
    assert errors == []
    assert len(found) > 0


def test_requirements_table_is_current() -> None:
    assert reqs.main(["--check"]) == 0


def _bound_scenarios(tmp_path: Path) -> list[dict[str, object]]:
    """The scenarios pytest binds across every test path, as the root conftest.py reports them."""
    out = tmp_path / "bindings.json"
    root = Path(__file__).parent.parent
    run = subprocess.run(  # noqa: S603 - our own pytest, fixed arguments
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-n",
            "0",
            "-p",
            "no:cacheprovider",
            f"--scenario-bindings={out}",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    bindings: list[dict[str, object]] = json.loads(out.read_text(encoding="utf-8"))
    return bindings


def test_every_implemented_scenario_runs_and_no_empty_one_passes(tmp_path: Path) -> None:
    """A scenario no test binds never runs; a bound one with no steps passes while checking nothing (#127, #128)."""
    bindings = _bound_scenarios(tmp_path)
    bound = {str(b["name"]).split()[0] for b in bindings}
    found, _ = reqs.parse()
    unbound = sorted(r.id for r in found if not r.pending and r.id not in bound)
    assert unbound == [], "implemented scenarios that no test binds"
    empty = sorted(str(b["name"]).split()[0] for b in bindings if b["steps"] == 0 and "pending" not in b["tags"])
    assert empty == [], "scenarios with no steps that are not tagged @pending"


def test_missing_persona_is_reported(tmp_path: Path) -> None:
    (tmp_path / "x.feature").write_text(
        "Feature: x\n  @ears_ubiquitous\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n"
    )
    _, errors = reqs.parse(tmp_path)
    assert errors and "persona" in errors[0]
