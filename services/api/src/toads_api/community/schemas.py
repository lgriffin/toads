"""Request and response shapes for the community routes. Every free-text field has a length cap."""

from __future__ import annotations

import enum
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

# Discord's own limits: 256 for an embed title, 4096 for an embed description.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
DayId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,32}$")]
Snowflake = Annotated[int, Field(gt=0, lt=2**63)]


def _single_spaced(value: object) -> object:
    """Trim a name and collapse runs of spaces to one; whitespace inside it other than spaces is left for the pattern
    to refuse."""
    return re.sub(r" {2,}", " ", value.strip()) if isinstance(value, str) else value


# WoW character names: letters only (accented letters allowed, no digits), and since WoW Forever one or more words
# split by a single space, 2 to 24 characters in all.
CharacterName = Annotated[
    str,
    StringConstraints(min_length=2, max_length=24, pattern=r"^[^\W\d_]+(?: [^\W\d_]+)*$"),
    BeforeValidator(_single_spaced),
]


class Role(enum.StrEnum):
    TANK = "Tank"
    HEALER = "Healer"
    MELEE = "Melee"
    RANGED = "Ranged"


class Visibility(enum.StrEnum):
    PUBLIC = "public"  # the outward story, readable without logging in
    GUILD = "guild"  # anyone signed in
    RAID_DAY = "raid_day"  # members of one raid day and the global tier


class PostOrigin(enum.StrEnum):
    HUB = "hub"
    DISCORD = "discord"


class PostStatus(enum.StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    HIDDEN = "hidden"


class Post(BaseModel):
    id: int
    title: str
    body: str
    author_name: str
    # Internal member ids ride along for storage and are never serialised to clients.
    author_id: int | None = Field(default=None, exclude=True)
    origin: PostOrigin
    visibility: Visibility
    raid_day: str | None = None
    status: PostStatus
    pinned: bool = False
    publish_to_discord: bool = False
    discord_channel_id: int | None = None
    discord_message_id: int | None = None
    edited_since_review: bool = False
    created_at: datetime
    published_at: datetime | None = None


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Tighter than other text: a post may go out as a Discord message, and the web form uses the same limits.
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    visibility: Visibility = Visibility.GUILD
    pinned: bool = False
    publish_to_discord: bool = False


class CurationAction(enum.StrEnum):
    PUBLISH = "publish"
    HIDE = "hide"


class CurationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: CurationAction
    # None keeps the audience the channel implies: its raid day, or the guild for guild-wide channels.
    visibility: Visibility | None = None


class ApplicationStatus(enum.StrEnum):
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    TRIAL_OFFERED = "trial_offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class ApplicationEvent(BaseModel):
    at: datetime
    actor_id: int = Field(exclude=True)
    actor_name: str
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    note: str = ""


class Application(BaseModel):
    id: int
    member_id: int
    applicant_name: str
    character_name: str
    class_name: str
    spec: str
    role: Role
    secondary_role: Role | None = None
    why_toads: str = ""
    raid_days: list[str]
    experience: str
    availability: str
    logs_url: str | None
    status: ApplicationStatus
    interview_channel_id: int | None = None
    # Set when the Toad Bot reported that it could not open the room; cleared when a room opens or is asked for again.
    interview_room_error: str | None = None
    # The room's Discord link for its applicant; only the applicant's own routes fill it in.
    interview_room_url: str | None = None
    events: list[ApplicationEvent]
    created_at: datetime


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_name: CharacterName
    class_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    # The primary role; secondary_role is the one they would also play, never the same one.
    role: Role
    secondary_role: Role | None = None
    why_toads: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    # Optional extras the recruit page no longer asks for; older clients and officers' notes still use them.
    spec: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    raid_days: list[DayId] = Field(default_factory=list, max_length=7)
    experience: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    availability: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    logs_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


class ApplicationTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: ApplicationStatus
    note: Note = ""


class Priority(enum.StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecruitmentNeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    spec: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    role: Role
    priority: Priority
    raid_days: list[DayId] = Field(default_factory=list, max_length=7)


class RaidNight(BaseModel):
    """A raid day an applicant can apply for, as the recruit page offers it."""

    id: DayId
    name: str


class Interviewer(BaseModel):
    """One Discord member on a raid night's interview panel (docs/recruitment.md)."""

    # A string: Discord ids are past the largest integer a browser can hold exactly.
    discord_user_id: Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]
    username: str
    display_name: str


class InterviewerAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discord_user_id: Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]


class InterviewPanel(BaseModel):
    """Who interviews a night's applicants. With no one on it, `fallback` (the community config's list) does."""

    raid_day: DayId
    interviewers: list[Interviewer]
    fallback: list[str]


class ClipProvider(enum.StrEnum):
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    STREAMABLE = "streamable"


class HighlightStatus(enum.StrEnum):
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    REJECTED = "rejected"


class Highlight(BaseModel):
    id: int
    title: str
    provider: ClipProvider
    clip_id: str
    submitted_by_id: int = Field(exclude=True)
    submitted_by: str
    raid_id: str | None = None
    boss: str | None = None
    visibility: Visibility
    status: HighlightStatus
    created_at: datetime


class HighlightCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
    raid_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")] | None = None
    boss: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None


class HighlightAction(enum.StrEnum):
    PUBLISH_PUBLIC = "publish_public"
    PUBLISH_GUILD = "publish_guild"
    REJECT = "reject"


class HighlightReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: HighlightAction


class SpotlightConsent(enum.StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    DECLINED = "declined"


class SpotlightStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class Spotlight(BaseModel):
    id: int
    member_id: int
    member_name: str
    character_name: str
    class_name: str
    headline: str
    body: str
    written_by_id: int = Field(exclude=True)
    written_by: str
    consent: SpotlightConsent
    status: SpotlightStatus
    created_at: datetime


class SpotlightCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: Snowflake
    character_name: CharacterName
    class_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    headline: Title
    body: Body


class ConsentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant: bool


class Progress(BaseModel):
    zone: str
    killed: int
    total: int


class PublicStory(BaseModel):
    guild: str
    realm: str
    tagline: str
    story: list[str]
    discord_invite: str | None
    progression: list[Progress]
    needs: list[RecruitmentNeed]
    posts: list[Post]
    highlights: list[Highlight]
    spotlights: list[Spotlight]


class DiscordMessageIn(BaseModel):
    """A message the bot saw in a mirrored channel. The API decides whether that channel is mirrored at all."""

    model_config = ConfigDict(extra="forbid")

    channel_id: Snowflake
    message_id: Snowflake
    author_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    content: Annotated[str, StringConstraints(max_length=4000)]
    created_at: datetime


class OutboxKind(enum.StrEnum):
    CREATE_INTERVIEW_ROOM = "create_interview_room"
    LOCK_INTERVIEW_ROOM = "lock_interview_room"
    POST_MESSAGE = "post_message"
    EDIT_MESSAGE = "edit_message"
    # DM one member (the bank desk's answer to their request, docs/bank-desk.md).
    SEND_DM = "send_dm"


class OutboxJob(BaseModel):
    """Work for the bot. The bot polls these with its service token and acks each one."""

    id: int
    kind: OutboxKind
    payload: dict[str, str | int | list[int] | list[str] | None]
    created_at: datetime
    done: bool = False


class OutboxAck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_id: Snowflake | None = None
    message_id: Snowflake | None = None
    # The job could not be done and retrying will not help (missing permission, applicant left the server): the bot
    # says why, and the hub shows it instead of waiting for a room that is not coming.
    error: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)] | None = None


class DeskSummary(BaseModel):
    """The raid leader desk on /hub: what is waiting on this officer, for the days they lead."""

    applications_waiting: int
    posts_to_curate: int
    highlights_to_review: int
    spotlights_awaiting_consent: int
