"""The Postgres repository keeps what the rules wrote: across instances, with UTC times and current member names.

test_community.py runs every route over this repository too; these cover what only storage can get wrong.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import Member
from toads_api.community.demo import PRINCIPALS, demo_service
from toads_api.community.schemas import (
    ApplicationCreate,
    ApplicationStatus,
    HighlightCreate,
    OutboxKind,
    PostCreate,
    Role,
    SpotlightCreate,
    Visibility,
)
from toads_api.community.sql_repository import SqlCommunityRepository

from conftest import sql_community_repository

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
WED_OFFICER = PRINCIPALS["Wednesday officer"].member_id
GLOBAL = PRINCIPALS["global officer"].member_id
RAIDER = PRINCIPALS["Wednesday raider"].member_id
APPLICANT = PRINCIPALS["applicant"].member_id
APPLICATION = ApplicationCreate(
    character_name="Mossbeard", class_name="Shaman", spec="Resto", role=Role.HEALER, experience="Cleared SSC."
)
SPOTLIGHT = SpotlightCreate(member_id=RAIDER, character_name="Hopscotch", class_name="Druid", headline="H", body="B")


def _repo() -> SqlCommunityRepository:
    repo = sql_community_repository()
    assert isinstance(repo, SqlCommunityRepository)
    return repo


def _fresh(repo: SqlCommunityRepository) -> SqlCommunityRepository:
    """A second repository on the same database, like another API process."""
    return SqlCommunityRepository(repo.db, progression_list=repo.progression_list)


def test_ids_are_unique_across_every_kind_of_record() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    post = svc.create_post(WED_OFFICER, "wed", PostCreate(title="Tonight", body="Bring flasks."))
    app = svc.apply(
        APPLICANT,
        ApplicationCreate(
            character_name="Mossbeard", class_name="Shaman", spec="Resto", role=Role.HEALER, experience="x"
        ),
    )
    assert post.id != app.id
    assert _repo().next_id() == 1  # a fresh database starts its own sequence


def test_an_application_and_its_history_survive_a_restart() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    app = svc.apply(
        APPLICANT,
        ApplicationCreate(
            character_name="Mossbeard", class_name="Shaman", spec="Resto", role=Role.HEALER, experience="x"
        ),
    )
    svc.open_interview_room(WED_OFFICER, None, app.id)
    svc.transition(WED_OFFICER, None, app.id, ApplicationStatus.TRIAL_OFFERED, "See you Wednesday")

    stored = _fresh(repo).get_application(app.id)
    assert stored is not None
    assert stored.status is ApplicationStatus.TRIAL_OFFERED
    assert [e.to_status for e in stored.events] == [
        ApplicationStatus.APPLIED,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.TRIAL_OFFERED,
    ]
    assert [e.actor_id for e in stored.events] == [APPLICANT, WED_OFFICER, WED_OFFICER]
    assert stored.events[-1].note == "See you Wednesday"
    # Saving again adds no duplicate history.
    repo.save_application(stored)
    again = _fresh(repo).get_application(app.id)
    assert again is not None
    assert len(again.events) == 3


def test_times_come_back_in_utc() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    post = svc.create_post(GLOBAL, None, PostCreate(title="Hello", body="World", visibility=Visibility.PUBLIC))
    stored = _fresh(repo).get_post(post.id)
    assert stored is not None
    assert stored.created_at == NOW
    assert stored.created_at.tzinfo is not None


def test_names_follow_the_members_directory() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    hl = svc.submit_highlight(RAIDER, HighlightCreate(title="Vashj", url="https://youtu.be/dQw4w9WgXcQ"))
    with repo.db.begin() as db:
        member = db.get(Member, RAIDER)
        assert member is not None
        member.display_name = "Hopscotch the Bold"
    stored = _fresh(repo).get_highlight(hl.id)
    assert stored is not None
    assert stored.submitted_by == "Hopscotch the Bold"
    # Member ids stay internal: they never appear in what the API returns.
    assert "submitted_by_id" not in stored.model_dump(mode="json")


def test_spotlight_consent_and_outbox_round_trip() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    sp = svc.create_spotlight(
        GLOBAL,
        SpotlightCreate(member_id=RAIDER, character_name="Hopscotch", class_name="Druid", headline="H", body="B"),
    )
    svc.decide_consent(RAIDER, sp.id, grant=True)
    svc.publish_spotlight(GLOBAL, sp.id)
    fresh = _fresh(repo)
    [public] = demo_service(lambda: NOW, fresh).published_spotlights()
    assert public.written_by == "Ribbitz"
    assert public.member_name == "Hopscotch"

    job = repo.enqueue(OutboxKind.POST_MESSAGE, {"channel_id": 333, "post_id": 1}, NOW)
    job.done = True
    repo.save_job(job)
    stored = fresh.get_job(job.id)
    assert stored is not None
    assert stored.done
    assert stored.payload == {"channel_id": 333, "post_id": 1}


def test_needs_are_replaced_as_a_whole() -> None:
    repo = _repo()
    demo_service(lambda: NOW, repo)
    assert [n.class_name for n in repo.needs()] == ["Shaman"]
    repo.set_needs([])
    assert _fresh(repo).needs() == []


def test_audit_rows_are_kept() -> None:
    repo = _repo()
    svc = demo_service(lambda: NOW, repo)
    sp = svc.create_spotlight(
        GLOBAL,
        SpotlightCreate(member_id=RAIDER, character_name="Hopscotch", class_name="Druid", headline="H", body="B"),
    )
    [record] = _fresh(repo).audit()
    assert (record.actor_member_id, record.action, record.target) == (GLOBAL, "spotlight.create", f"spotlight:{sp.id}")
    assert record.at == NOW
