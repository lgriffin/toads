"""Raid days, their Discord roles and channels are configuration, not code (REQ-HUB-DAY-020)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from toads_api.rbac.permissions import HubRole, Principal


class RaidDayChannels(BaseModel):
    raid_logs: int | None = None
    signups: int | None = None
    bank_requests: int | None = None


class RaidDay(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,32}$")
    name: str
    raider_roles: list[int] = []
    trial_roles: list[int] = []
    officer_roles: list[int] = []
    channels: RaidDayChannels = RaidDayChannels()


class RaidDaysConfig(BaseModel):
    global_officer_roles: list[int] = []
    raid_days: list[RaidDay] = []

    @classmethod
    def load(cls, path: Path) -> RaidDaysConfig:
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def all_role_ids(self) -> set[int]:
        ids = set(self.global_officer_roles)
        for day in self.raid_days:
            ids.update(day.raider_roles, day.trial_roles, day.officer_roles)
        return ids

    def principal_for(self, member_id: int, discord_role_ids: set[int]) -> Principal:
        """Map a member's Discord role ids to hub roles; several matches give the highest per day."""
        day_roles: dict[str, HubRole] = {}
        for day in self.raid_days:
            role = HubRole.MEMBER
            if discord_role_ids & set(day.trial_roles):
                role = HubRole.TRIAL
            if discord_role_ids & set(day.raider_roles):
                role = HubRole.RAIDER
            if discord_role_ids & set(day.officer_roles):
                role = HubRole.OFFICER
            if role is not HubRole.MEMBER:
                day_roles[day.id] = role
        return Principal(
            member_id=member_id,
            global_officer=bool(discord_role_ids & set(self.global_officer_roles)),
            day_roles=day_roles,
        )
