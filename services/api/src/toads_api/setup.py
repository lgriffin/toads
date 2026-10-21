"""The first sign-in setup (REQ-HUB-ME-007, docs/setup.md): a trial or raider names their main, specs and alts.

Sign-in sends a trial or raider to /setup until they finish it (`needs_setup`); anyone may rerun it from the account
menu. The page claims characters from the guild's logs through the claim routes and sets specs through
/api/me/specs; this module holds what those do not:

- GET    /api/me/setup                    whether setup is done, and the characters named that the logs have not seen
- POST   /api/me/setup/characters         name a character by name and class: claimed at once if the logs know it,
                                          else kept until they do
- DELETE /api/me/setup/characters/{id}    drop a named character
- POST   /api/me/setup/main               make a character just claimed the first main
- POST   /api/me/setup/done               finish setup

A member's first main is theirs to name, while they hold no approved character but that one. After that, changing the
main is a main swap that officers approve (toads_api.main_swaps). Every route acts on the caller's own member id,
taken from the session, never from the request.
"""

from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import anyio
from fastapi import APIRouter, Depends, HTTPException, Response, status
from hub_db import CharacterClaim, ClaimStatus, DeclaredCharacter, Member, main_claim
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from toads_api import audit
from toads_api.claims import ClaimOut, claim_character
from toads_api.comps.catalog import CLASSES
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal, can
from toads_api.services import Services

router = APIRouter()

Claimant = Annotated[Principal, Depends(require(Permission.CLAIM_CHARACTER))]
Hub = Annotated[Services, Depends(get_services)]


class DeclareIn(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    wow_class: str = Field(max_length=16)
    main: bool = False


class MainIn(BaseModel):
    character_id: int = Field(gt=0)


class DeclaredOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    wow_class: str
    main: bool


class MainOut(BaseModel):
    name: str
    # approved: their main now; pending: claimed and named main, waiting for an officer; not_in_logs: named here and
    # waiting for its first logged raid with the guild.
    status: Literal["approved", "pending", "not_in_logs"]


class SetupOut(BaseModel):
    done: bool
    main: MainOut | None
    # Characters the member named that the guild's logs have not seen yet, oldest first.
    declared: list[DeclaredOut]
    # Whether the member may still name their first main here (they hold no approved character but the one named).
    main_open: bool


class DeclaredResult(BaseModel):
    """A named character: a claim when the logs know it, else the kept row."""

    claim: ClaimOut | None = None
    declared: DeclaredOut | None = None


def _fold(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).split()).casefold()


def _tidy(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).split())


def needs_setup(services: Services, principal: Principal) -> bool:
    """True while a trial or raider (anyone who may claim characters) has not finished the setup."""
    if not can(principal, Permission.CLAIM_CHARACTER):
        return False
    with services.db() as db:
        member = db.get(Member, principal.member_id)
        return member is not None and member.setup_done_at is None


def _main_open(db: Session, member: Member | None, character_id: int | None = None) -> bool:
    """A member names their first main while they hold no approved character but `character_id`: from then on, the
    main changes only by a main swap."""
    if member is None:
        return False
    approved = db.scalars(
        select(CharacterClaim.character_id).where(
            CharacterClaim.member_id == member.id, CharacterClaim.status == ClaimStatus.APPROVED
        )
    )
    return all(cid == character_id for cid in approved)


def _known(services: Services, name: str) -> int | None:
    """The id of the character the guild's logs know by exactly this name, if any."""
    folded = _fold(name)
    return next((c.id for c in services.characters.search(name) if _fold(c.name) == folded), None)


def _declared(db: Session, member_id: int) -> list[DeclaredCharacter]:
    return list(
        db.scalars(
            select(DeclaredCharacter).where(DeclaredCharacter.member_id == member_id).order_by(DeclaredCharacter.id)
        )
    )


def _claim_as_main(services: Services, principal: Principal, character_id: int) -> None:
    with services.db.begin() as db:
        member = db.get(Member, principal.member_id)
        if _main_open(db, member, character_id) and member is not None:
            member.main_character_id = character_id
            audit.record(
                db, actor=principal.member_id, action="setup.main", target=f"character {character_id}", raid_day=None
            )


def _resolve(services: Services, principal: Principal) -> list[ClaimOut]:
    """Turn the named characters the logs now know into claims, as a claim from the picker would be. A character
    someone else holds stays named, for an officer to sort out."""
    with services.db() as db:
        rows = [(d.id, d.name, d.main) for d in _declared(db, principal.member_id)]
    made: list[ClaimOut] = []
    for row_id, name, main in rows:
        character_id = _known(services, name)
        if character_id is None:
            continue
        try:
            claim, _ = claim_character(services, principal, character_id)
        except (HTTPException, IntegrityError):
            continue
        made.append(claim)
        if main:
            _claim_as_main(services, principal, character_id)
        with services.db.begin() as db:
            row = db.get(DeclaredCharacter, row_id)
            if row is not None:
                db.delete(row)
    return made


def _main(db: Session, member: Member | None, declared: list[DeclaredCharacter]) -> MainOut | None:
    """The member's main as setup shows it: their main now, else the claim they named main, else the named main the
    logs have not seen."""
    if member is None:
        return None
    claims = list(
        db.scalars(
            select(CharacterClaim)
            .where(CharacterClaim.member_id == member.id, CharacterClaim.status != ClaimStatus.REJECTED)
            .order_by(CharacterClaim.id)
        )
    )
    approved = [c for c in claims if c.status is ClaimStatus.APPROVED]
    if (main := main_claim(member.main_character_id, approved)) is not None:
        return MainOut(name=main.character_name, status="approved")
    if (named := next((c for c in claims if c.character_id == member.main_character_id), None)) is not None:
        return MainOut(name=named.character_name, status="pending")
    if (kept := next((d for d in declared if d.main), None)) is not None:
        return MainOut(name=kept.name, status="not_in_logs")
    return None


def _state(services: Services, principal: Principal) -> SetupOut:
    with services.db() as db:
        member = db.get(Member, principal.member_id)
        declared = _declared(db, principal.member_id)
        return SetupOut(
            done=member is not None and member.setup_done_at is not None,
            main=_main(db, member, declared),
            declared=[DeclaredOut.model_validate(d) for d in declared],
            main_open=_main_open(db, member),
        )


async def _notify(services: Services, claims: list[ClaimOut]) -> None:
    # The same FYI or ask the claim route sends, so a named character reaches #officers like any other claim.
    for claim in claims:
        await services.notifier.notify_officers(
            {
                "kind": "claim_pending" if claim.status is ClaimStatus.PENDING else "claim_auto_approved",
                "claim_id": claim.id,
                "character": claim.character_name,
                "raid_day": claim.raid_day_id,
            }
        )


@router.get("/api/me/setup")
async def my_setup(principal: Claimant, services: Hub) -> SetupOut:
    await _notify(services, await anyio.to_thread.run_sync(_resolve, services, principal))
    return await anyio.to_thread.run_sync(_state, services, principal)


def _declare(services: Services, principal: Principal, body: DeclareIn) -> DeclaredResult:
    name = _tidy(body.name)
    if body.wow_class not in CLASSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown class")
    with services.db() as db:
        if body.main and not _main_open(db, db.get(Member, principal.member_id)):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Ask your officers to swap your main")
    character_id = _known(services, name)
    if character_id is not None:
        claim, _ = claim_character(services, principal, character_id)
        if body.main:
            _claim_as_main(services, principal, character_id)
        return DeclaredResult(claim=claim)
    with services.db.begin() as db:
        mine = _declared(db, principal.member_id)
        if any(_fold(d.name) == _fold(name) for d in mine):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Already named")
        if body.main:
            for d in mine:
                d.main = False
        row = DeclaredCharacter(member_id=principal.member_id, name=name, wow_class=body.wow_class, main=body.main)
        db.add(row)
        db.flush()
        return DeclaredResult(declared=DeclaredOut.model_validate(row))


@router.post("/api/me/setup/characters", status_code=status.HTTP_201_CREATED)
async def declare_character(body: DeclareIn, principal: Claimant, services: Hub) -> DeclaredResult:
    try:
        result = await anyio.to_thread.run_sync(_declare, services, principal, body)
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Character already claimed") from None
    if result.claim is not None:
        await _notify(services, [result.claim])
    return result


def _drop(services: Services, principal: Principal, row_id: int) -> None:
    with services.db.begin() as db:
        row = db.get(DeclaredCharacter, row_id)
        if row is None or row.member_id != principal.member_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such character")
        db.delete(row)


@router.delete("/api/me/setup/characters/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_character(row_id: int, principal: Claimant, services: Hub) -> Response:
    await anyio.to_thread.run_sync(_drop, services, principal, row_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _set_main(services: Services, principal: Principal, character_id: int) -> None:
    with services.db.begin() as db:
        claim = db.scalar(
            select(CharacterClaim).where(
                CharacterClaim.character_id == character_id,
                CharacterClaim.member_id == principal.member_id,
                CharacterClaim.status != ClaimStatus.REJECTED,
            )
        )
        if claim is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim the character first")
        member = db.get(Member, principal.member_id)
        if member is None or not _main_open(db, member, character_id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Ask your officers to swap your main")
        member.main_character_id = character_id
        # A named main the logs have not seen gives way to the one just claimed.
        for d in _declared(db, principal.member_id):
            d.main = False
        audit.record(
            db, actor=principal.member_id, action="setup.main", target=f"character {character_id}", raid_day=None
        )


@router.post("/api/me/setup/main", status_code=status.HTTP_204_NO_CONTENT)
async def set_first_main(body: MainIn, principal: Claimant, services: Hub) -> Response:
    await anyio.to_thread.run_sync(_set_main, services, principal, body.character_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _finish(services: Services, principal: Principal) -> dict[str, Any]:
    with services.db.begin() as db:
        member = db.get(Member, principal.member_id)
        if member is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such member")
        member.setup_done_at = datetime.fromtimestamp(services.clock(), UTC)
        return {"done": True}


@router.post("/api/me/setup/done")
async def finish_setup(principal: Claimant, services: Hub) -> dict[str, Any]:
    return await anyio.to_thread.run_sync(_finish, services, principal)
