"""Tables the hub needs that the analyzer never had (members, claims, audit, community, raid sheets, WCL keys, ...)."""

from hub_db.absences import MemberAbsence
from hub_db.awards import MemberAward
from hub_db.bank import EVERY_DAY, BankGrant, BankGrantToken
from hub_db.community import (
    Application,
    ApplicationEvent,
    BotOutbox,
    CommunityId,
    CommunityPost,
    Highlight,
    InterviewPanelist,
    RecruitmentNeed,
    Spotlight,
)
from hub_db.comps import MemberSpec, RaidComp
from hub_db.credentials import (
    CredentialCipher,
    CredentialDecryptError,
    StoredWclCredentials,
    WclCredential,
    WclCredentialStatus,
)
from hub_db.logs import LogIndex, LogRaid
from hub_db.models import (
    AnalyzerBadgePage,
    AnalyzerHomePage,
    AnalyzerPerformancePage,
    AuditEntry,
    Base,
    CharacterClaim,
    ClaimStatus,
    Member,
    MemberHomeLayout,
)
from hub_db.officer_board import OfficerBoardCard
from hub_db.officer_grants import OfficerGrant
from hub_db.raid_sheets import RaidSheetSnapshot
from hub_db.reference import ReferenceComparison, ReferenceJob, ReferenceLogin, ReferencePage
from hub_db.role_badges import DiscordRoleBadge

__all__ = [
    "EVERY_DAY",
    "AnalyzerBadgePage",
    "AnalyzerHomePage",
    "AnalyzerPerformancePage",
    "Application",
    "ApplicationEvent",
    "AuditEntry",
    "BankGrant",
    "BankGrantToken",
    "Base",
    "BotOutbox",
    "CharacterClaim",
    "ClaimStatus",
    "CommunityId",
    "CommunityPost",
    "CredentialCipher",
    "CredentialDecryptError",
    "DiscordRoleBadge",
    "Highlight",
    "InterviewPanelist",
    "LogIndex",
    "LogRaid",
    "Member",
    "MemberAbsence",
    "MemberAward",
    "MemberHomeLayout",
    "MemberSpec",
    "OfficerBoardCard",
    "OfficerGrant",
    "RaidComp",
    "RaidSheetSnapshot",
    "RecruitmentNeed",
    "ReferenceComparison",
    "ReferenceJob",
    "ReferenceLogin",
    "ReferencePage",
    "Spotlight",
    "StoredWclCredentials",
    "WclCredential",
    "WclCredentialStatus",
]
