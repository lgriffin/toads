"""The bank request desk: items members ask the guild bank for from Discord (`/bankrequest`) or the site, and the
officers' answer to each (docs/bank-desk.md).

It lives in the hub, not ToadsBank: it needs no bank snapshot, so officers can work requests before the bank's stock
is imported. Every row is kept after it is answered, so each member's asks stay on the record.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class BankItemRequest(Base):
    __tablename__ = "bank_item_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Who asked: their Discord user id (they need not have signed in to the hub) and their server name at the time.
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    requester_name: Mapped[str] = mapped_column(String(100))
    item: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer)
    # Where it was asked: "discord" or "site".
    source: Mapped[str] = mapped_column(String(16), default="site")
    # pending, approved or denied.
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # The officer's answer: their message to the member, who gave it and when.
    officer_message: Mapped[str | None] = mapped_column(String(500))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    decided_by_name: Mapped[str | None] = mapped_column(String(100))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The Toad Bot job that DMs the member the answer (bot_outbox), so the desk can say whether it reached them.
    notice_job_id: Mapped[int | None] = mapped_column(Integer)
