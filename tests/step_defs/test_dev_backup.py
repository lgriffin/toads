"""REQ-DEV-OPS-002: nightly snapshots of the hub and rewinding to one (ADMIN_GUIDE.md section 13)."""

import configparser
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
DRILL = ROOT / "tests" / "backup" / "drill.sh"


@scenario(
    str(ROOT / "tests" / "features" / "dev_ops.feature"),
    "REQ-DEV-OPS-002 When the nightly backup runs, the server shall keep a checked snapshot of the hub database, "
    "config, env files and certificates and copy it off the server encrypted, and a restore shall rewind the hub to "
    "any kept night, keeping the replaced database for undo",
)
def test_nightly_backup() -> None:
    pass


def _unit(name: str) -> configparser.ConfigParser:
    unit = configparser.ConfigParser(interpolation=None)
    unit.optionxform = str  # type: ignore[assignment,method-assign]
    unit.read_string((ROOT / "infra" / "systemd" / name).read_text(encoding="utf-8"))
    return unit


@given("the production server's backup timer and scripts", target_fixture="backup")
def backup() -> dict[str, Any]:
    return {
        "service": _unit("toads-backup.service"),
        "timer": _unit("toads-backup.timer"),
        "lib": (ROOT / "scripts" / "backup-lib.sh").read_text(encoding="utf-8"),
    }


@then("the backup runs every night as the toads user and catches up a night missed while the server was off")
def nightly(backup: dict[str, Any]) -> None:
    timer, service = backup["timer"], backup["service"]
    assert re.fullmatch(r"\*-\*-\* \d\d:\d\d:00 UTC", timer["Timer"]["OnCalendar"])
    assert timer["Timer"]["Persistent"] == "true"
    assert timer["Install"]["WantedBy"] == "timers.target"
    assert service["Service"]["User"] == "toads"
    assert service["Service"]["ExecStart"] == "/opt/toads/scripts/backup.sh nightly"
    assert "docker.service" in service["Unit"]["Requires"]


@then("restic runs from a pinned image and the off-server settings stay out of git")
def pinned_and_ignored(backup: dict[str, Any]) -> None:
    dockerfile = (ROOT / "infra" / "backup" / "Dockerfile").read_text(encoding="utf-8")
    bases = dict(re.findall(r"^FROM (restic/restic|rclone/rclone):(\S+)", dockerfile, re.M))
    assert set(bases) == {"restic/restic", "rclone/rclone"}
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", version) for version in bases.values())
    image = re.search(r"^RESTIC_IMAGE=(\S+)$", backup["lib"], re.M)
    assert image and image.group(1) == f"toads-restic:{bases['restic/restic']}-rclone{bases['rclone/rclone']}"
    git = shutil.which("git")
    assert git
    ignored = subprocess.run([git, "check-ignore", "-q", "infra/.env.backup"], cwd=ROOT, check=False)  # noqa: S603 - fixed args
    assert ignored.returncode == 0
    example = (ROOT / "infra" / ".env.backup.example").read_text(encoding="utf-8")
    assert re.search(r"^RESTIC_PASSWORD=replace-me$", example, re.M)
    assert re.search(r"^RESTIC_REPOSITORY=$", example, re.M)


@then("CI runs the backup and restore drill against a real Postgres and restic repository")
def drill_in_ci() -> None:
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    steps = ci["jobs"]["backup"]["steps"]
    assert any(step.get("env", {}).get("TOADS_BACKUP_DRILL") == "1" for step in steps)
    assert DRILL.exists() and os.access(DRILL, os.X_OK)


@pytest.mark.skipif(os.environ.get("TOADS_BACKUP_DRILL") != "1", reason="needs Docker; CI's backup job sets it")
def test_backup_and_restore_drill() -> None:
    """Two nights of snapshots, a rewind, an undo, a rewind from the off-server copy alone, a tampered snapshot."""
    bash = shutil.which("bash")
    assert bash
    result = subprocess.run(  # noqa: S603 - our own script
        [bash, str(DRILL)], cwd=ROOT, check=False, capture_output=True, text=True, timeout=900
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
