"""The feature files are the spec: every scenario is traceable and docs/requirements.md is current."""

import importlib.util
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


def test_missing_persona_is_reported(tmp_path: Path) -> None:
    (tmp_path / "x.feature").write_text(
        "Feature: x\n  @ears_ubiquitous\n  Scenario: REQ-HUB-X-001 The hub shall do a thing\n"
    )
    _, errors = reqs.parse(tmp_path)
    assert errors and "persona" in errors[0]
