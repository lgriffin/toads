"""Where the API looks up characters seen in the guild's logs.

Characters belong to wcl-store (lgriffin/warcraftlogs_project), which is not published yet. Until it
is, production uses `NoCharacters` (every claim answers 404) and tests use `InMemoryCharacters`.
The claim flow resolves names server-side only: a client-sent name would let anyone auto-approve a
claim on someone else's character by sending their own nickname (REQ-HUB-CLAIM-001).
"""

from __future__ import annotations

from typing import Protocol


class CharacterDirectory(Protocol):
    def name_of(self, character_id: int) -> str | None: ...


class NoCharacters:
    """Placeholder until wcl-store's characters table is wired in."""

    def name_of(self, character_id: int) -> str | None:
        return None


class InMemoryCharacters:
    def __init__(self, names: dict[int, str] | None = None) -> None:
        self.names: dict[int, str] = dict(names or {})

    def name_of(self, character_id: int) -> str | None:
        return self.names.get(character_id)
