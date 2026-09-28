"""Raid days, their Discord roles and channels are configuration, not code (REQ-HUB-DAY-020)."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, Field, field_validator

from toads_api.rbac.permissions import HubRole, Principal


class UnknownDiscordRoleError(RuntimeError):
    """A configured role id is not a role in the Discord server (REQ-HUB-DAY-022)."""


class RaidDayChannels(BaseModel):
    raid_logs: int | None = None
    signups: int | None = None
    bank_requests: int | None = None


class RaidDay(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,32}$")
    name: str
    # When the raid starts, "HH:MM" in the config's timezone. The hub home falls back to it for the next raid while no
    # Discord scheduled event is coming up; the weekday comes from the day's name (or raid_sheets.yaml's weekdays).
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    raider_roles: list[int] = []
    trial_roles: list[int] = []
    officer_roles: list[int] = []
    channels: RaidDayChannels = RaidDayChannels()


class RaidDaysConfig(BaseModel):
    # The realm's server time, which raid start times are written in (Spineshatter is an EU realm).
    timezone: str = "Europe/Paris"
    global_officer_roles: list[int] = []
    raid_days: list[RaidDay] = []

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone {value!r}") from exc
        return value

    @classmethod
    def load(cls, path: Path) -> RaidDaysConfig:
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def all_role_ids(self) -> set[int]:
        ids = set(self.global_officer_roles)
        for day in self.raid_days:
            ids.update(day.raider_roles, day.trial_roles, day.officer_roles)
        return ids

    def day(self, day_id: str) -> RaidDay | None:
        return next((d for d in self.raid_days if d.id == day_id), None)

    def check_roles_exist(self, server_role_ids: set[int]) -> None:
        """Fail naming the raid day and role when a configured role id is not in the server (REQ-HUB-DAY-022)."""
        unknown = [("global officers", r) for r in self.global_officer_roles if r not in server_role_ids]
        for day in self.raid_days:
            for kind, ids in (("trial", day.trial_roles), ("raider", day.raider_roles), ("officer", day.officer_roles)):
                unknown += [(f"raid day {day.id!r} {kind}", r) for r in ids if r not in server_role_ids]
        if unknown:
            names = "; ".join(f"{where} role {role_id}" for where, role_id in unknown)
            raise UnknownDiscordRoleError(f"Discord server has no such role: {names}")

    def principal_for(self, member_id: int, discord_role_ids: set[int], display_name: str = "") -> Principal:
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
            display_name=display_name,
            global_officer=bool(discord_role_ids & set(self.global_officer_roles)),
            day_roles=day_roles,
        )
