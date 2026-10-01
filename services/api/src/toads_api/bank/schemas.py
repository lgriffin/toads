"""Request bodies the hub accepts for the bank, in the ToadsBank contract's own (camelCase) names. The hub checks the
shape and forwards only these fields; ToadsBank owns every rule about stock, sources and request states."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# Ids ToadsBank hands out (src_1, req_1, an import's id) travel in URL paths: keep them to a safe alphabet.
ID = r"^[A-Za-z0-9_-]{1,64}$"
EntityId = Annotated[str, Field(pattern=ID)]
DiscordId = Annotated[str, Field(pattern=r"^\d{1,20}$")]
# A session takes at most 800 parts of at most 1,800 characters (TB-DM-07), a little over 1.4 million characters.
MAX_PASTE = 1_500_000


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PartsIn(_Body):
    text: str = Field(min_length=1, max_length=MAX_PASTE)


class SourceCreate(_Body):
    name: str = Field(min_length=1, max_length=100)
    guild: str = Field(min_length=1, max_length=100)
    realm: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=2, max_length=8)
    audience: Literal["members", "officers"] = "members"
    raidDay: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")
    managers: list[DiscordId] = Field(default_factory=list, max_length=50)


class SourcePatch(_Body):
    expectedRevision: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    audience: Literal["members", "officers"] | None = None
    raidDay: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")
    managers: list[DiscordId] | None = Field(default=None, max_length=50)


class RequestCreate(_Body):
    sourceId: EntityId
    itemId: int = Field(gt=0, lt=2**31)
    quantity: int = Field(gt=0, le=10_000)
    character: str = Field(min_length=1, max_length=24)
    note: str = Field(default="", max_length=200)
    occurrenceId: EntityId | None = None
    waitlist: bool = False


class Revision(_Body):
    expectedRevision: int = Field(ge=0)


class Decision(Revision):
    note: str | None = Field(default=None, max_length=200)


class Delivery(Revision):
    quantity: int = Field(gt=0, le=10_000)


class BankMe(BaseModel):
    """What the bank page and bot need to know about the caller: whether the bank is set up, and where they may act as
    an officer (manager routes are scoped to a raid day, like every officer power)."""

    configured: bool
    discord_user_id: str | None
    display_name: str
    global_officer: bool
    officer_days: list[str]
    # The raid days whose import and queue routes the caller may use: their officer days, plus any day a grant covers
    # (every day for a grant with no raid day).
    import_days: list[str] = []
    manage_days: list[str] = []
    # Whether the caller may list bank grants (the global tier) and grant, revoke and mint tokens (super admins).
    sees_grants: bool = False
    manages_grants: bool = False
    super_admin: bool = False
    # The caller is the break-glass admin (docs/admin.md), and, for the global tier, who that is (a Discord id).
    break_glass: bool = False
    break_glass_admin: str | None = None


class EventAck(BaseModel):
    accepted: bool = True
    duplicate: bool = False
    actions: int = 0
