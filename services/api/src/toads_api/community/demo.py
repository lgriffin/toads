"""A small, fully fake guild for tests and local development: two raid days, their officers, and a few members.

Nothing here is real data; ids are made up and every name is a toad pun.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from toads_api.community.config import CommunityConfig, MirroredChannel
from toads_api.community.schemas import Priority, Progress, RecruitmentNeed, Role
from toads_api.community.store import CommunityStore, MemberCard
from toads_api.rbac import HubRole, Principal, RaidDay, RaidDaysConfig

GLOBAL_ROLE, WED_OFFICER_ROLE, SUN_OFFICER_ROLE = 900, 12, 22
ANNOUNCEMENTS, WED_CHAT, GUILD_POSTS, WED_POSTS, INTERVIEWS = 111, 222, 333, 444, 555

PRINCIPALS: dict[str, Principal] = {
    "global officer": Principal(member_id=1, global_officer=True),
    "Wednesday officer": Principal(member_id=2, day_roles={"wed": HubRole.OFFICER}),
    "Sunday officer": Principal(member_id=3, day_roles={"sun": HubRole.OFFICER}),
    "Wednesday raider": Principal(member_id=4, day_roles={"wed": HubRole.RAIDER}),
    "applicant": Principal(member_id=5),
    "Sunday trial": Principal(member_id=6, day_roles={"sun": HubRole.TRIAL}),
}

MEMBERS = {
    1: MemberCard("Ribbitz", 10_001),
    2: MemberCard("Croakley", 10_002),
    3: MemberCard("Pondkeeper", 10_003),
    4: MemberCard("Hopscotch", 10_004),
    5: MemberCard("Newtonian", 10_005),
    6: MemberCard("Tadpole", 10_006),
}


def demo_store(clock: Callable[[], datetime]) -> CommunityStore:
    raid_days = RaidDaysConfig(
        global_officer_roles=[GLOBAL_ROLE],
        raid_days=[
            RaidDay(id="wed", name="Wednesday", raider_roles=[11], officer_roles=[WED_OFFICER_ROLE]),
            RaidDay(id="sun", name="Sunday", raider_roles=[21], officer_roles=[SUN_OFFICER_ROLE]),
        ],
    )
    config = CommunityConfig(
        tagline="A relaxed but prepared TBC guild on Spineshatter.",
        story=["We started in a Barrens pond and have been hopping through raids since 2006."],
        discord_invite="https://discord.gg/toads",
        mirrored_channels=[
            MirroredChannel(channel_id=ANNOUNCEMENTS),
            MirroredChannel(channel_id=WED_CHAT, raid_day="wed"),
        ],
        post_channels={"guild": GUILD_POSTS, "wed": WED_POSTS},
        interview_category_id=INTERVIEWS,
    )
    store = CommunityStore(config=config, raid_days=raid_days, clock=clock, members=dict(MEMBERS))
    store.needs = [RecruitmentNeed(class_name="Shaman", spec="Restoration", role=Role.HEALER, priority=Priority.HIGH)]
    store.progression = [Progress(zone="Serpentshrine Cavern", killed=5, total=6)]
    return store
