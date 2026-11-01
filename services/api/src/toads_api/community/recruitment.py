"""The application pipeline. Transitions are a closed table; anything else is refused with 409."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit

from toads_api.community.schemas import ApplicationStatus as S
from toads_api.community.schemas import Role
from toads_api.comps.catalog import CLASSES, SPECS, Spec
from toads_api.comps.catalog import Role as SeatRole

TRANSITIONS: dict[S, frozenset[S]] = {
    # Officers may accept straight from the Decisions panel; a trial raid is an optional step before it.
    S.APPLIED: frozenset({S.INTERVIEWING, S.ACCEPTED, S.DECLINED, S.WITHDRAWN}),
    S.INTERVIEWING: frozenset({S.TRIAL_OFFERED, S.ACCEPTED, S.DECLINED, S.WITHDRAWN}),
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

# Spam guards. Every applicant has already signed in with Discord and joined the server, so the cheap abuse left is
# throwaway Discord accounts and an apply-withdraw loop, each of which would open a new interview room.
MIN_DISCORD_ACCOUNT_AGE_DAYS = 7
APPLICATION_LIMIT = 3
APPLICATION_WINDOW_DAYS = 7

# The Decisions panel shows what was decided over this many days, so officers see the Toad Bot's word on it.
DECIDED_WINDOW_DAYS = 14

# A raid night's interview panel (docs/recruitment.md): enough for every officer, small enough to fit one room.
PANEL_LIMIT = 10

# Recruitment needs are picked from the comp builder's specs; the homepage groups them under the community roles.
NEED_ROLES: dict[SeatRole, Role] = {
    SeatRole.TANK: Role.TANK,
    SeatRole.HEALER: Role.HEALER,
    SeatRole.MELEE: Role.MELEE,
    SeatRole.RANGED: Role.RANGED,
}
_SPEC_BY_NAME = {(CLASSES[s.wow_class], s.name): s for s in SPECS.values()}


def spec_for(class_name: str, spec: str) -> Spec | None:
    """The catalogue spec a stored need names ("Shaman", "Restoration"), or None for one the catalogue lacks."""
    return _SPEC_BY_NAME.get((class_name, spec))


# Discord ids are snowflakes: the top 42 bits are milliseconds since this epoch, so an id says when the account began.
DISCORD_EPOCH_MS = 1_420_070_400_000

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


def discord_account_created(discord_user_id: int) -> datetime:
    return datetime.fromtimestamp(((discord_user_id >> 22) + DISCORD_EPOCH_MS) / 1000, tz=UTC)


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
