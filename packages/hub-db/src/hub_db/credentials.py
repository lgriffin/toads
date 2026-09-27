"""Members' own Warcraft Logs API keys, encrypted at rest.

A member may save their own Warcraft Logs client id and secret; requests made on their behalf then use their key
and its rate-limit budget instead of the guild's. Both values are stored as Fernet tokens (MultiFernet, so keys
can be rotated: the first key encrypts, every key decrypts). Each plaintext is bound to its member id before
encryption, so a ciphertext copied into another member's row fails to decrypt instead of lending them the key.

The API writes these rows; the worker reads them. Plaintext never leaves this module except to the caller that
asked for it, and nothing here logs.
"""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from hub_db.models import Base


def _now() -> datetime:
    return datetime.now(UTC)


class WclCredentialStatus(enum.StrEnum):
    # Saved, not yet used.
    UNVERIFIED = "unverified"
    # Warcraft Logs issued a token for it the last time the worker used it.
    WORKING = "working"
    # Warcraft Logs refused it; the member's requests fall back to the guild key until they save a new one.
    REJECTED = "rejected"


class WclCredential(Base):
    __tablename__ = "wcl_credentials"

    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    client_id_encrypted: Mapped[str] = mapped_column(Text)
    client_secret_encrypted: Mapped[str] = mapped_column(Text)
    # The client id's last four characters, so the settings page can show which key is saved without decrypting.
    client_id_hint: Mapped[str] = mapped_column(String(8))
    status: Mapped[WclCredentialStatus] = mapped_column(
        Enum(WclCredentialStatus, native_enum=False, values_callable=lambda e: [m.value for m in e], length=16),
        default=WclCredentialStatus.UNVERIFIED,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredentialDecryptError(Exception):
    """The stored key cannot be read: the encryption key was rotated away, or the row was tampered with."""


class CredentialCipher:
    """Encrypts members' keys. `keys` are Fernet keys, newest first; the first one encrypts."""

    def __init__(self, keys: Sequence[str]) -> None:
        keys = [k.strip() for k in keys if k.strip()]
        if not keys:
            raise ValueError("at least one credential encryption key is required")
        try:
            self._fernet = MultiFernet([Fernet(k.encode("ascii")) for k in keys])
        except (ValueError, UnicodeError) as exc:
            # Never echo the value: it is (or was meant to be) a secret.
            raise ValueError("credential keys must be Fernet keys; generate one with `just credentials-key`") from exc

    @classmethod
    def from_setting(cls, value: str) -> CredentialCipher:
        """Build from TOADS_CREDENTIALS_KEYS: comma-separated Fernet keys, newest first."""
        return cls(value.split(","))

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("ascii")

    def encrypt(self, member_id: int, plaintext: str) -> str:
        return self._fernet.encrypt(f"{member_id}:{plaintext}".encode()).decode("ascii")

    def decrypt(self, member_id: int, token: str) -> str:
        try:
            value = self._fernet.decrypt(token.encode("ascii")).decode()
        except (InvalidToken, UnicodeError) as exc:
            raise CredentialDecryptError from exc
        owner, sep, plaintext = value.partition(":")
        if not sep or owner != str(member_id):
            raise CredentialDecryptError
        return plaintext


@dataclass(frozen=True)
class StoredWclCredentials:
    """A member's decrypted key. repr hides the secret so it cannot reach a log line or traceback by accident."""

    member_id: int
    client_id: str
    client_secret: str
    status: WclCredentialStatus

    def __repr__(self) -> str:
        hint = self.client_id[-4:]
        return f"StoredWclCredentials(member_id={self.member_id}, client_id=...{hint}, status={self.status})"


def save_wcl_credentials(
    db: Session, cipher: CredentialCipher, member_id: int, client_id: str, client_secret: str
) -> WclCredential:
    row = db.get(WclCredential, member_id)
    if row is None:
        row = WclCredential(member_id=member_id)
        db.add(row)
    row.client_id_encrypted = cipher.encrypt(member_id, client_id)
    row.client_secret_encrypted = cipher.encrypt(member_id, client_secret)
    row.client_id_hint = client_id[-4:]
    row.status = WclCredentialStatus.UNVERIFIED
    row.updated_at = _now()
    row.checked_at = None
    db.flush()
    return row


def load_wcl_credentials(db: Session, cipher: CredentialCipher, member_id: int) -> StoredWclCredentials | None:
    """The member's key, or None when they have not saved one. Raises CredentialDecryptError when unreadable."""
    row = db.get(WclCredential, member_id)
    if row is None:
        return None
    return StoredWclCredentials(
        member_id=member_id,
        client_id=cipher.decrypt(member_id, row.client_id_encrypted),
        client_secret=cipher.decrypt(member_id, row.client_secret_encrypted),
        status=row.status,
    )


def mark_wcl_credentials(db: Session, member_id: int, status: WclCredentialStatus) -> None:
    row = db.get(WclCredential, member_id)
    if row is not None:
        row.status = status
        row.checked_at = _now()


def delete_wcl_credentials(db: Session, member_id: int) -> bool:
    row = db.get(WclCredential, member_id)
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True
