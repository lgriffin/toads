"""The bank request desk's rules (docs/bank-desk.md), over the in-memory repository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from toads_api.bank_desk.repository import Decision, InMemoryBankDeskRepository, RequestStatus
from toads_api.bank_desk.service import BankDeskError, BankDeskService, notice_for

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)


def desk() -> tuple[BankDeskService, InMemoryBankDeskRepository]:
    repo = InMemoryBankDeskRepository()
    return BankDeskService(repo, clock=lambda: NOW), repo


def test_an_ask_is_kept_tidy_and_pending() -> None:
    service, _ = desk()
    r = service.ask(7, "  Hop\nscotch ", "  Flask of\n Relentless   Assault ", 4, "discord")
    assert (r.requester_name, r.item, r.quantity, r.source) == (
        "Hop scotch",
        "Flask of Relentless Assault",
        4,
        "discord",
    )
    assert (r.status, r.created_at, r.notice) == (RequestStatus.PENDING, NOW, None)
    assert service.ask(8, "   ", "Drums", 1, "site").requester_name == "8"


@pytest.mark.parametrize(
    ("item", "quantity", "source", "why"),
    [
        ("  ", 1, "site", "which item"),
        ("x" * 101, 1, "site", "at most 100"),
        ("Drums", 0, "site", "between 1 and 1000"),
        ("Drums", 1001, "site", "between 1 and 1000"),
        ("Drums", 1, "carrier pigeon", "source"),
    ],
)
def test_bad_asks_are_refused(item: str, quantity: int, source: str, why: str) -> None:
    with pytest.raises(BankDeskError, match=why) as exc:
        desk()[0].ask(7, "Hopscotch", item, quantity, source)
    assert exc.value.status == 422


def test_an_answer_is_recorded_once_and_dms_the_member() -> None:
    service, repo = desk()
    asked = service.ask(7, "Hopscotch", "Drums of Battle", 2, "discord")
    done = service.decide(asked.id, RequestStatus.DENIED, "  Short this week ", 1, "Croak", "wed")
    assert (done.status, done.officer_message, done.decided_by_name, done.decided_at) == (
        RequestStatus.DENIED,
        "Short this week",
        "Croak",
        NOW,
    )
    assert repo.notices == [
        (7, "Your guild bank request #1 for Drums of Battle x2 was denied by Croak.\n> Short this week")
    ]
    with pytest.raises(BankDeskError, match="already denied") as exc:
        service.decide(asked.id, RequestStatus.APPROVED, "", 1, "Croak")
    assert exc.value.status == 409
    assert len(repo.notices) == 1


def test_answers_are_checked() -> None:
    service, _ = desk()
    asked = service.ask(7, "Hopscotch", "Drums", 1, "site")
    with pytest.raises(BankDeskError, match="Approve or deny"):
        service.decide(asked.id, RequestStatus.PENDING, "", 1, "Croak")
    with pytest.raises(BankDeskError, match="at most 500"):
        service.decide(asked.id, RequestStatus.APPROVED, "x" * 501, 1, "Croak")
    with pytest.raises(BankDeskError, match="No such request") as exc:
        service.decide(99, RequestStatus.APPROVED, "", 1, "Croak")
    assert exc.value.status == 404


def test_an_answer_that_loses_a_race_is_refused() -> None:
    service, repo = desk()
    asked = service.ask(7, "Hopscotch", "Drums", 1, "site")
    first = Decision(RequestStatus.APPROVED, "", 2, "Ribbit", NOW, "first")
    real_get = repo.get
    # Another officer answers between the service's read and its write.
    repo.get = lambda request_id: (real_get(request_id), repo.decide(request_id, first))[0]  # type: ignore[method-assign]
    with pytest.raises(BankDeskError, match="already answered") as exc:
        service.decide(asked.id, RequestStatus.DENIED, "", 1, "Croak")
    assert exc.value.status == 409


def test_history_is_per_member_newest_first() -> None:
    service, _ = desk()
    for who, item in ((7, "A"), (8, "B"), (7, "C")):
        service.ask(who, "x", item, 1, "site")
    assert [r.item for r in service.history(7)] == ["C", "A"]
    assert [r.item for r in service.requests()] == ["C", "B", "A"]
    assert service.requests(RequestStatus.APPROVED) == []


def test_an_approval_says_a_banker_will_hand_it_over() -> None:
    service, _ = desk()
    asked = service.ask(7, "Hopscotch", "Drums", 1, "site")
    text = notice_for(asked, RequestStatus.APPROVED, "", "Croak")
    assert text == "Your guild bank request #1 for Drums x1 was approved by Croak.\nA banker will hand it over in game."
