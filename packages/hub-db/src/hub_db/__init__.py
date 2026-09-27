"""Tables the hub needs that the analyzer never had (members, claims, audit, community, raid sheets, ...)."""

from hub_db.community import (
    Application,
    ApplicationEvent,
    BotOutbox,
    CommunityId,
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
    "CommunityId",
    "CommunityPost",
    "Highlight",
    "Member",
    "RaidSheetSnapshot",
    "RecruitmentNeed",
    "Spotlight",
]
