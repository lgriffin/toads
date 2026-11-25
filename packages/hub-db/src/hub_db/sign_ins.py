"""Sign-ins: one row each time a member signs in to the hub (docs/sign-ins.md).

The officers' sign-in audit reads these by day. `raid_days` is the member's raid nights at that sign-in, so a night's
officers see the sign-ins of the people who were on their night then, even after a member moves nights.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class SignIn(Base):
    """One completed Discord sign-in. Rows are never updated."""

    __tablename__ = "sign_ins"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    # The raid nights the member's Discord roles put them on at this sign-in; empty for a member on no night.
    raid_days: Mapped[list[str]] = mapped_column(JSON, default=list)
