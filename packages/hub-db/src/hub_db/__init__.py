"""Tables the hub needs that the analyzer never had (members, claims, audit, community, members' WCL keys, ...)."""

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
from hub_db.credentials import (
    CredentialCipher,
    CredentialDecryptError,
    StoredWclCredentials,
    WclCredential,
    WclCredentialStatus,
)
from hub_db.models import AuditEntry, Base, CharacterClaim, ClaimStatus, Member

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
    "CredentialCipher",
    "CredentialDecryptError",
    "Highlight",
    "Member",
    "RecruitmentNeed",
    "Spotlight",
    "StoredWclCredentials",
    "WclCredential",
    "WclCredentialStatus",
]
