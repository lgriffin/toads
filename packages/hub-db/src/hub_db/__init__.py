"""Tables the hub needs that the analyzer never had (members, claims, audit, community, raid sheets, ...)."""

from hub_db.community import (
    Application,
    ApplicationEvent,
    BotOutbox,
    CommunityPost,
    Highlight,
    RecruitmentNeed,
    Spotlight,
)
from hub_db.models import AuditEntry, Base, CharacterClaim, ClaimStatus, Member
from hub_db.raid_sheets import RaidSheetSnapshot

__all__ = [
    "Application",
    "ApplicationEvent",
    "AuditEntry",
    "Base",
    "BotOutbox",
    "CharacterClaim",
    "ClaimStatus",
    "CommunityPost",
    "Highlight",
    "Member",
    "RaidSheetSnapshot",
    "RecruitmentNeed",
    "Spotlight",
]
