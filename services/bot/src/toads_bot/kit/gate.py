"""Who may make a bot do what. There is no auth or permission model for bots yet, so every bot runs with OpenGate;
a role-backed gate slots in here later without touching the bindings, which already ask before acting."""

from __future__ import annotations

from typing import Protocol


class Gate(Protocol):
    def allows(self, user_id: int, capability: str) -> bool: ...


class OpenGate:
    """Everyone may do everything. The placeholder until bot permissions are designed."""

    def allows(self, user_id: int, capability: str) -> bool:
        return True
