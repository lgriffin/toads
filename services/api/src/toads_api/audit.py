"""Audit log writes (REQ-HUB-AUDIT-001, REQ-HUB-DAY-011, REQ-HUB-DAY-017). Rows are never updated or deleted."""

from __future__ import annotations

from hub_db import AuditEntry
from sqlalchemy.orm import Session


def record(
    db: Session, *, actor: int, action: str, target: str, raid_day: str | None, detail: str | None = None
) -> None:
    db.add(
        AuditEntry(
            actor_member_id=actor,
            action=action,
            target=target[:200],
            raid_day_id=raid_day,
            detail=detail[:500] if detail else None,
        )
    )
