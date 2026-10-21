"""Pin the analyzer's packages to a release of lgriffin/warcraftlogs_project (REQ-DEV-CI-008).

`current` prints the tag (or commit) that wcl-core, wcl-store and wcl-app are pinned to in the root pyproject.toml and
fails unless all three agree. `pin <tag>` rewrites all three to that release tag. The Analyzer release workflow runs
both; run `uv lock` after `pin`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
PACKAGES = ("wcl-core", "wcl-store", "wcl-app")
# Only plain releases: a tag such as v4.6.0-rc1 never reaches the site.
RELEASE_TAG = re.compile(r"v\d+\.\d+\.\d+")
_PIN = re.compile(r'\b(?:rev|tag) = "([^"]+)"')


def _source_line(text: str, package: str) -> re.Match[str]:
    match = re.search(
        rf'^{re.escape(package)} = \{{ git = "https://github.com/lgriffin/warcraftlogs_project".*$', text, re.M
    )
    if match is None:
        raise ValueError(f"{package} has no warcraftlogs_project git source in pyproject.toml")
    return match


def current(text: str) -> str:
    """The one tag or commit every analyzer package is pinned to."""
    pins = set()
    for package in PACKAGES:
        found = _PIN.search(_source_line(text, package).group(0))
        if found is None:
            raise ValueError(f"{package} is not pinned to a rev or tag")
        pins.add(found.group(1))
    if len(pins) != 1:
        raise ValueError(f"the analyzer packages are pinned to different versions: {sorted(pins)}")
    return pins.pop()


def pin(text: str, tag: str) -> str:
    """`text` with every analyzer package pinned to the release `tag`."""
    if not RELEASE_TAG.fullmatch(tag):
        raise ValueError(f"{tag!r} is not a release tag like v4.5.0")
    for package in PACKAGES:
        line = _source_line(text, package)
        pinned, count = _PIN.subn(f'tag = "{tag}"', line.group(0))
        if count != 1:
            raise ValueError(f"{package} is not pinned to exactly one rev or tag")
        text = text[: line.start()] + pinned + text[line.end() :]
    return text


def main(argv: list[str]) -> int:
    text = PYPROJECT.read_text(encoding="utf-8")
    try:
        if argv == ["current"]:
            sys.stdout.write(current(text) + "\n")
            return 0
        if len(argv) == 2 and argv[0] == "pin":
            PYPROJECT.write_text(pin(text, argv[1]), encoding="utf-8")
            return 0
    except ValueError as error:
        sys.stderr.write(f"analyzer_release: {error}\n")
        return 1
    sys.stderr.write("usage: analyzer_release.py current | pin <tag>\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
