"""AccountRepository over hub-db. Members' Warcraft Logs keys are encrypted by hub-db's CredentialCipher, so plaintext
exists only in the request that saves a key and in the worker that uses it."""

from __future__ import annotations

from collections.abc import Iterable

from hub_db import CharacterClaim, ClaimStatus, CredentialCipher, Member, WclCredential
from hub_db.credentials import delete_wcl_credentials, save_wcl_credentials
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.account.repository import MemberNames, WclKeyRecord


class SqlAccountRepository:
    def __init__(self, db: sessionmaker[Session], cipher: CredentialCipher) -> None:
        self._db = db
        self._cipher = cipher

    def names(self, member_ids: Iterable[int] | None = None) -> list[MemberNames]:
        with self._db() as db:
            members = select(Member).order_by(Member.id)
            claims = select(CharacterClaim).where(CharacterClaim.status == ClaimStatus.APPROVED)
            if member_ids is not None:
                ids = list(member_ids)
                members = members.where(Member.id.in_(ids))
                claims = claims.where(CharacterClaim.member_id.in_(ids))
            owned: dict[int, dict[int, str]] = {}
            for c in db.scalars(claims):
                owned.setdefault(c.member_id, {})[c.character_id] = c.character_name
            return [
                MemberNames(
                    member_id=m.id,
                    discord_user_id=m.discord_user_id,
                    discord_name=m.display_name,
                    name_source=m.name_source,
                    name_character_id=m.name_character_id,
                    characters=owned.get(m.id, {}),
                )
                for m in db.scalars(members)
            ]

    def set_name(self, member_id: int, source: str, character_id: int | None) -> None:
        with self._db.begin() as db:
            member = db.get(Member, member_id)
            if member is None:
                raise LookupError(member_id)
            member.name_source = source
            member.name_character_id = character_id

    @staticmethod
    def _record(row: WclCredential) -> WclKeyRecord:
        return WclKeyRecord(
            client_id_hint=row.client_id_hint,
            status=row.status.value,
            updated_at=row.updated_at,
            checked_at=row.checked_at,
        )

    def wcl_key(self, member_id: int) -> WclKeyRecord | None:
        with self._db() as db:
            row = db.get(WclCredential, member_id)
            return None if row is None else self._record(row)

    def save_wcl_key(self, member_id: int, client_id: str, client_secret: str) -> WclKeyRecord:
        with self._db.begin() as db:
            return self._record(save_wcl_credentials(db, self._cipher, member_id, client_id, client_secret))

    def delete_wcl_key(self, member_id: int) -> bool:
        with self._db.begin() as db:
            return delete_wcl_credentials(db, member_id)
