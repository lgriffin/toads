"""Tables the hub needs that the analyzer never had (members, claims, audit, community, raid sheets, WCL keys, ...)."""

from hub_db.absences import MemberAbsence
from hub_db.awards import MemberAward
from hub_db.bank import EVERY_DAY, BankGrant, BankGrantToken
from hub_db.bank_desk import BankItemRequest
from hub_db.community import (
    Application,
    ApplicationEvent,
    ApplicationNote,
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
from hub_db.gallery import GalleryPhoto, GalleryPhotoFile, LiveStream, PhotoOfTheWeek, TrustedChannel
from hub_db.logs import LogIndex, LogRaid
from hub_db.models import (
    AnalyzerBadgePage,
    AnalyzerCharacterBuild,
    AnalyzerCharacterPage,
    AnalyzerHomePage,
    AnalyzerPerformancePage,
    AuditEntry,
    Base,
    CharacterClaim,
    ClaimStatus,
    MainSwapRequest,
    Member,
    MemberHomeLayout,
    NightHomePage,
    main_claim,
)
from hub_db.officer_board import NightLink, OfficerBoardCard
from hub_db.officer_grants import OfficerGrant
from hub_db.professions import GuildCrafter, MemberProfession
from hub_db.raid_sheets import RaidSheetSnapshot
from hub_db.reference import ReferenceComparison, ReferenceJob, ReferenceLogin, ReferencePage
from hub_db.role_badges import DiscordRoleBadge
from hub_db.setup import DeclaredCharacter
from hub_db.strategy import NightRaid, StrategyDoc

__all__ = [
    "EVERY_DAY",
    "AnalyzerBadgePage",
    "AnalyzerCharacterBuild",
    "AnalyzerCharacterPage",
    "AnalyzerHomePage",
    "AnalyzerPerformancePage",
    "Application",
    "ApplicationEvent",
    "ApplicationNote",
    "AuditEntry",
    "BankGrant",
    "BankGrantToken",
    "BankItemRequest",
    "Base",
    "BotOutbox",
    "CharacterClaim",
    "ClaimStatus",
    "CommunityId",
    "CommunityPost",
    "CredentialCipher",
    "CredentialDecryptError",
    "DeclaredCharacter",
    "DiscordRoleBadge",
    "GalleryPhoto",
    "GalleryPhotoFile",
    "GuildCrafter",
    "Highlight",
    "InterviewPanelist",
    "LiveStream",
    "LogIndex",
    "LogRaid",
    "MainSwapRequest",
    "Member",
    "MemberAbsence",
    "MemberAward",
    "MemberHomeLayout",
    "MemberProfession",
    "MemberSpec",
    "NightHomePage",
    "NightLink",
    "NightRaid",
    "OfficerBoardCard",
    "OfficerGrant",
    "PhotoOfTheWeek",
    "RaidComp",
    "RaidSheetSnapshot",
    "RecruitmentNeed",
    "ReferenceComparison",
    "ReferenceJob",
    "ReferenceLogin",
    "ReferencePage",
    "Spotlight",
    "StoredWclCredentials",
    "StrategyDoc",
    "TrustedChannel",
    "WclCredential",
    "WclCredentialStatus",
    "main_claim",
]
