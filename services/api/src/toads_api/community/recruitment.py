"""The application pipeline. Transitions are a closed table; anything else is refused with 409."""

from __future__ import annotations

from urllib.parse import urlsplit

from toads_api.community.schemas import ApplicationStatus as S

TRANSITIONS: dict[S, frozenset[S]] = {
    S.APPLIED: frozenset({S.INTERVIEWING, S.DECLINED, S.WITHDRAWN}),
    S.INTERVIEWING: frozenset({S.TRIAL_OFFERED, S.DECLINED, S.WITHDRAWN}),
    S.TRIAL_OFFERED: frozenset({S.ACCEPTED, S.DECLINED, S.WITHDRAWN}),
    S.ACCEPTED: frozenset(),
    S.DECLINED: frozenset(),
    S.WITHDRAWN: frozenset(),
}
OPEN = frozenset(s for s, nxt in TRANSITIONS.items() if nxt)
FINAL = frozenset(S) - OPEN
# Only the applicant withdraws; officers move everything else.
APPLICANT_ONLY = frozenset({S.WITHDRAWN})

# An applicant who was declined can apply again after this many days.
REAPPLY_COOLDOWN_DAYS = 30

LOGS_HOSTS = frozenset(
    {
        "warcraftlogs.com",
        "www.warcraftlogs.com",
        "classic.warcraftlogs.com",
        "fresh.warcraftlogs.com",
        "sod.warcraftlogs.com",
    }
)


def can_transition(current: S, to: S) -> bool:
    return to in TRANSITIONS[current]


def valid_logs_url(url: str) -> bool:
    """An applicant's logs link must be a plain https link to Warcraft Logs; we only ever render it as a link."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.username is None
        and parts.password is None
        and port is None
        and (parts.hostname or "").lower() in LOGS_HOSTS
        and not any(c.isspace() for c in url)
    )
