"""Rules for a member's own settings. No RBAC, web framework or storage imports: the routes decide who may call,
and the repository decides where things live."""

from __future__ import annotations

import enum
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from toads_api.account.repository import AccountRepository, MemberNames


class NameSource(enum.StrEnum):
    # The member's Discord server nickname (the default).
    DISCORD = "discord"
    # One of the member's approved characters.
    CHARACTER = "character"


class AccountError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# Warcraft Logs client ids are UUIDs today; accept any id-shaped value so a format change on their side does not
# lock members out. Secrets: printable ASCII without spaces. Both are checked here rather than trusted blindly.
_CLIENT_ID = re.compile(r"[A-Za-z0-9-]{8,100}")
_CLIENT_SECRET = re.compile(r"[\x21-\x7e]{8,200}")


@dataclass(frozen=True)
class NameOption:
    source: NameSource
    name: str
    character_id: int | None = None


@dataclass(frozen=True)
class WclKeyView:
    """A saved key as the member sees it: which key (last four characters of the id) and whether it works."""

    client_id_hint: str
    status: str
    updated_at: datetime
    checked_at: datetime | None


@dataclass(frozen=True)
class AccountSettings:
    member_id: int
    shown_name: str
    name_source: NameSource
    name_character_id: int | None
    name_options: list[NameOption]
    # None: the member's requests use the guild's key.
    wcl_key: WclKeyView | None


@dataclass(frozen=True)
class DirectoryEntry:
    member_id: int
    shown_name: str
    discord_user_id: int


def shown_name(names: MemberNames) -> str:
    """The name the hub shows. A character name holds only while the member has an approved claim on it, so
    unclaiming (or an officer reassigning the claim) falls back to the Discord name without any clean-up."""
    if names.name_source == NameSource.CHARACTER and names.name_character_id in names.characters:
        return names.characters[names.name_character_id]
    return names.discord_name


class AccountService:
    def __init__(self, repo: AccountRepository) -> None:
        self.repo = repo

    def _names(self, member_id: int) -> MemberNames:
        found = self.repo.names([member_id])
        if not found:
            raise AccountError("Unknown member", status=404)
        return found[0]

    # ---------------------------------------------------------------- names

    def shown_name(self, member_id: int) -> str:
        return shown_name(self._names(member_id))

    def directory(self) -> list[DirectoryEntry]:
        """Every member by the name they chose, sorted by that name."""
        entries = [DirectoryEntry(n.member_id, shown_name(n), n.discord_user_id) for n in self.repo.names()]
        return sorted(entries, key=lambda e: (e.shown_name.casefold(), e.member_id))

    def shown_names(self, member_ids: Iterable[int]) -> dict[int, str]:
        return {n.member_id: shown_name(n) for n in self.repo.names(member_ids)}

    def choose_name(self, member_id: int, source: NameSource, character_id: int | None = None) -> AccountSettings:
        names = self._names(member_id)
        if source is NameSource.DISCORD:
            character_id = None
        elif character_id is None or character_id not in names.characters:
            # Only approved claims: a free choice would let anyone go by someone else's character.
            raise AccountError("Choose one of your approved characters", status=422)
        self.repo.set_name(member_id, source.value, character_id)
        return self.settings(member_id)

    # ------------------------------------------------------ Warcraft Logs key

    def save_wcl_key(self, member_id: int, client_id: str, client_secret: str) -> AccountSettings:
        client_id, client_secret = client_id.strip(), client_secret.strip()
        if not _CLIENT_ID.fullmatch(client_id):
            raise AccountError("That does not look like a Warcraft Logs client id", status=422)
        if not _CLIENT_SECRET.fullmatch(client_secret):
            raise AccountError("That does not look like a Warcraft Logs client secret", status=422)
        self._names(member_id)
        self.repo.save_wcl_key(member_id, client_id, client_secret)
        return self.settings(member_id)

    def remove_wcl_key(self, member_id: int) -> AccountSettings:
        self.repo.delete_wcl_key(member_id)
        return self.settings(member_id)

    # ------------------------------------------------------------- summary

    def settings(self, member_id: int) -> AccountSettings:
        names = self._names(member_id)
        options = [NameOption(NameSource.DISCORD, names.discord_name)] + [
            NameOption(NameSource.CHARACTER, name, cid)
            for cid, name in sorted(names.characters.items(), key=lambda item: item[1].casefold())
        ]
        # The effective choice: a character choice whose claim has gone reads back as the Discord name.
        on_character = names.name_source == NameSource.CHARACTER and names.name_character_id in names.characters
        source = NameSource.CHARACTER if on_character else NameSource.DISCORD
        record = self.repo.wcl_key(member_id)
        return AccountSettings(
            member_id=member_id,
            shown_name=shown_name(names),
            name_source=source,
            name_character_id=names.name_character_id if source is NameSource.CHARACTER else None,
            name_options=options,
            wcl_key=None
            if record is None
            else WclKeyView(record.client_id_hint, record.status, record.updated_at, record.checked_at),
        )
