"""Report code handling shared by the nightly sync, /log and "Import by URL" (REQ-CORE-SEC-002)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

REPORT_CODE = re.compile(r"^[A-Za-z0-9]{16}$")
_WCL_HOSTS = {"warcraftlogs.com", "classic.warcraftlogs.com", "fresh.warcraftlogs.com", "vanilla.warcraftlogs.com"}


class InvalidReportCodeError(ValueError):
    pass


def validate_report_code(code: str) -> str:
    if not REPORT_CODE.fullmatch(code):
        raise InvalidReportCodeError("report code must be 16 letters or digits")
    return code


def parse_report_input(value: str) -> str:
    """Accept a bare code or a Warcraft Logs report URL and return the validated code."""
    value = value.strip()
    if "/" not in value:
        return validate_report_code(value)
    url = urlparse(value if "://" in value else f"https://{value}")
    host = (url.hostname or "").removeprefix("www.")
    if host not in _WCL_HOSTS:
        raise InvalidReportCodeError("not a Warcraft Logs URL")
    parts = [p for p in url.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "reports":
        raise InvalidReportCodeError("not a report URL")
    return validate_report_code(parts[1])
