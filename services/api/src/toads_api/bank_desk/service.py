"""Rules for the bank request desk. No RBAC, web framework or storage imports: the routes decide who may call (any
member asks; officers, or a member granted the bank's upkeep, answer) and the repository decides where requests live."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from toads_api.bank_desk.repository import (
    BankDeskRepository,
    BankRequestRecord,
    Decision,
    NewBankRequest,
    RequestStatus,
)

ITEM_LIMIT = 100
NAME_LIMIT = 100
MESSAGE_LIMIT = 500
MAX_QUANTITY = 1000
SOURCES = frozenset({"discord", "site"})


class BankDeskError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _clean(text: str) -> str:
    """One line of text: runs of whitespace (newlines included) become one space."""
    return " ".join(text.split())


def notice_for(record: BankRequestRecord, status: RequestStatus, message: str, officer: str) -> str:
    """The DM the member gets: what they asked for, the answer, who gave it and the officer's message."""
    verdict = "approved" if status is RequestStatus.APPROVED else "denied"
    lines = [f"Your guild bank request #{record.id} for {record.item} x{record.quantity} was {verdict} by {officer}."]
    if message:
        lines.append(f"> {message}")
    if status is RequestStatus.APPROVED:
        lines.append("A banker will hand it over in game.")
    return "\n".join(lines)


class BankDeskService:
    def __init__(self, repo: BankDeskRepository, clock: Callable[[], datetime]) -> None:
        self._repo = repo
        self._clock = clock

    def ask(self, discord_user_id: int, name: str, item: str, quantity: int, source: str) -> BankRequestRecord:
        item = _clean(item)
        if not item:
            raise BankDeskError("Say which item you need", 422)
        if len(item) > ITEM_LIMIT:
            raise BankDeskError(f"An item name is at most {ITEM_LIMIT} characters", 422)
        if not 1 <= quantity <= MAX_QUANTITY:
            raise BankDeskError(f"Ask for between 1 and {MAX_QUANTITY}", 422)
        if source not in SOURCES:
            raise BankDeskError("Unknown request source", 422)
        shown = _clean(name)[:NAME_LIMIT] or str(discord_user_id)
        return self._repo.add(NewBankRequest(discord_user_id, shown, item, quantity, source, self._clock()))

    def requests(self, status: RequestStatus | None = None) -> list[BankRequestRecord]:
        return self._repo.listed(status)

    def history(self, discord_user_id: int) -> list[BankRequestRecord]:
        """Every request one member has made, newest first: their record of asks and answers."""
        return self._repo.listed(discord_user_id=discord_user_id)

    def decide(
        self,
        request_id: int,
        status: RequestStatus,
        message: str,
        officer_id: int,
        officer_name: str,
        raid_day: str | None = None,
    ) -> BankRequestRecord:
        """Approve or deny a pending request with an optional message; the Toad Bot DMs the member the answer."""
        if status is RequestStatus.PENDING:
            raise BankDeskError("Approve or deny", 422)
        message = message.strip()
        if len(message) > MESSAGE_LIMIT:
            raise BankDeskError(f"A message is at most {MESSAGE_LIMIT} characters", 422)
        record = self._repo.get(request_id)
        if record is None:
            raise BankDeskError("No such request", 404)
        if record.status is not RequestStatus.PENDING:
            raise BankDeskError(f"That request was already {record.status.value}", 409)
        officer = _clean(officer_name)[:NAME_LIMIT] or "an officer"
        notice = notice_for(record, status, message, officer)
        decision = Decision(status, message, officer_id, officer, self._clock(), notice, raid_day)
        decided = self._repo.decide(request_id, decision)
        if decided is None:
            # Another officer answered it between the read and the write.
            raise BankDeskError("That request was already answered", 409)
        return decided
