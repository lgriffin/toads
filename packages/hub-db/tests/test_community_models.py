import pytest
from hub_db import Application, ApplicationEvent, Base, BotOutbox, CommunityPost, Member, Spotlight
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def _member(session: Session, n: int) -> Member:
    m = Member(discord_user_id=n, display_name=f"Toad{n}")
    session.add(m)
    session.flush()
    return m


def test_one_post_per_discord_message(session: Session) -> None:
    common = {"title": "t", "body": "b", "author_name": "a", "origin": "discord", "visibility": "guild"}
    session.add_all([CommunityPost(discord_message_id=5, **common), CommunityPost(discord_message_id=5, **common)])
    with pytest.raises(IntegrityError):
        session.flush()


def test_hub_posts_need_no_discord_message(session: Session) -> None:
    common = {"title": "t", "body": "b", "author_name": "a", "origin": "hub", "visibility": "guild"}
    session.add_all([CommunityPost(**common), CommunityPost(**common)])
    session.flush()


def test_application_round_trip(session: Session) -> None:
    m = _member(session, 1)
    app = Application(
        member_id=m.id,
        character_name="Mossbeard",
        class_name="Shaman",
        spec="Restoration",
        role="Healer",
        raid_days=["wed"],
        experience="SSC",
    )
    session.add(app)
    session.flush()
    session.add(ApplicationEvent(application_id=app.id, actor_member_id=m.id, to_status="applied"))
    session.flush()
    assert app.status == "applied"
    assert session.get(Application, app.id) is not None
    assert session.get(Application, app.id).raid_days == ["wed"]  # type: ignore[union-attr]


def test_spotlight_defaults_to_draft_pending_consent(session: Session) -> None:
    m = _member(session, 2)
    sp = Spotlight(member_id=m.id, character_name="Hop", class_name="Rogue", headline="h", body="b", written_by=m.id)
    session.add(sp)
    session.flush()
    assert (sp.status, sp.consent) == ("draft", "pending")


def test_outbox_payload_is_json(session: Session) -> None:
    job = BotOutbox(kind="create_interview_room", payload={"application_id": 1, "officer_role_ids": [12, 900]})
    session.add(job)
    session.flush()
    assert job.done is False
    assert job.payload["officer_role_ids"] == [12, 900]
