import pytest
from hub_db import Base, CharacterClaim, ClaimStatus, Member
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_claim_defaults_to_pending(session: Session) -> None:
    m = Member(discord_user_id=1, display_name="Toad")
    session.add(m)
    session.flush()
    claim = CharacterClaim(member_id=m.id, character_id=42, character_name="Toad")
    session.add(claim)
    session.flush()
    assert claim.status is ClaimStatus.PENDING


def test_one_character_one_owner(session: Session) -> None:
    a = Member(discord_user_id=1, display_name="A")
    b = Member(discord_user_id=2, display_name="B")
    session.add_all([a, b])
    session.flush()
    session.add_all(
        [
            CharacterClaim(member_id=a.id, character_id=7, character_name="X"),
            CharacterClaim(member_id=b.id, character_id=7, character_name="X"),
        ]
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_status_is_stored_by_value(session: Session) -> None:
    m = Member(discord_user_id=1, display_name="Toad")
    session.add(m)
    session.flush()
    session.add(CharacterClaim(member_id=m.id, character_id=1, character_name="Toad", status=ClaimStatus.APPROVED))
    session.flush()
    assert session.execute(text("SELECT status FROM character_claims")).scalar_one() == "approved"
