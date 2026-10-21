"""One-way ratchets (REQ-DEV-CI-003): a pull request may raise a floor in pyproject.toml, never lower it.

    python scripts/ratchet.py               # compare against origin/main
    python scripts/ratchet.py --base <ref>  # compare against another ref

Each floor is a dotted path into pyproject.toml. A floor missing on the base passes (it is new); one missing here
fails, since deleting a floor lowers it to nothing. Stdlib only.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FLOORS = ["tool.coverage.report.fail_under"]


def floor(config: dict[str, Any], path: str) -> float | None:
    value: Any = config
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return float(value)


def lowered(base: dict[str, Any], head: dict[str, Any]) -> list[str]:
    """Each floor `head` lowers or drops against `base`, as a line to print."""
    problems = []
    for path in FLOORS:
        was, now = floor(base, path), floor(head, path)
        if was is None:
            continue
        if now is None:
            problems.append(f"{path} was {was:g} and is gone")
        elif now < was:
            problems.append(f"{path} went down from {was:g} to {now:g}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="origin/main", help="the ref whose floors this tree must not go below")
    args = parser.parse_args(argv)
    shown = subprocess.run(  # noqa: S603 - git with fixed arguments and a ref the caller names
        ["git", "show", f"{args.base}:pyproject.toml"],  # noqa: S607 - git from PATH, as in CI
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if shown.returncode != 0:
        print(f"cannot read pyproject.toml at {args.base}: {shown.stderr.strip()}", file=sys.stderr)
        return 1
    head = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    problems = lowered(tomllib.loads(shown.stdout), head)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print("Floors only go up: raise the coverage or the tests, not the floor.", file=sys.stderr)
        return 1
    print(", ".join(f"{path} = {floor(head, path):g}" for path in FLOORS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
