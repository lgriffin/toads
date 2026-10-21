"""Awards: the milestone, achievement and title toads officers give members (docs/awards.md).

Which awards exist is the API's catalogue (`toads_api.awards.catalog`); a row here only names one by id, so retiring
an award from the catalogue never needs a migration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class MemberAward(Base):
    """One award held by one member. A monthly award (Raider of the Month) carries the month it was for and a weekly
    honour (Raider of the Week, Sunder King) the ISO week, so the same member can hold it for several months or weeks;
    every other award is held once, with an empty period."""

    __tablename__ = "member_awards"
    __table_args__ = (UniqueConstraint("member_id", "award_id", "period", name="uq_member_award"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    award_id: Mapped[str] = mapped_column(String(48), index=True)
    # "YYYY-MM" for a monthly award, "YYYY-Www" for a weekly honour, "" for every other award (never NULL, so the
    # unique constraint holds).
    period: Mapped[str] = mapped_column(String(8), default="", server_default="")
    # Why it was given, in the officer's words; shown with the award.
    note: Mapped[str | None] = mapped_column(String(200))
    awarded_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
