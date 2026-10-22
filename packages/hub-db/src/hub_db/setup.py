"""The first sign-in setup (docs/setup.md): characters a member names that the guild's logs have not seen yet.

A member picks their main and alts from the characters in the guild's logs, which become claims. A character the logs
have never seen (a new alt, or a main that has not raided with us) is kept here by name and class until it appears,
when the hub turns it into an ordinary claim and drops the row.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class DeclaredCharacter(Base):
    """A character a member says is theirs, not yet in the guild's logs. `main` marks the one they named as main."""

    __tablename__ = "declared_characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    # A class id from the comps catalogue (toads_api.comps.catalog.CLASSES).
    wow_class: Mapped[str] = mapped_column(String(16))
    main: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
