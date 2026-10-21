"""Character claims (REQ-HUB-CLAIM-001/003/005, REQ-HUB-PRIV-003, REQ-HUB-DAY-010/011).

Members find a character by name (GET /api/characters) and claim it by its wcl-store id; who is claiming comes from
their Discord sign-in, and the name is looked up server-side. A name that matches the
member's server nickname is approved at once, anything else waits for an officer of the claimant's
raid nights: the nights their Discord roles put them on now (REQ-HUB-CLAIM-005). Officer routes take the raid day
from the path only, and a claim outside that night is refused with 403 and an audit row. Claims from members on no
night go to the global tier's /api/admin/claims, which also decides any night's claims.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Collection
from datetime import UTC, datetime
from typing import Literal, NoReturn

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from hub_db import CharacterClaim, ClaimStatus, Member
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from toads_api import audit
from toads_api.characters import Character
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

router = APIRouter()


class ClaimIn(BaseModel):
    character_id: int = Field(gt=0)


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class ReassignIn(BaseModel):
    member_id: int = Field(gt=0)


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    character_id: int
    character_name: str
    raid_day_id: str | None
    status: ClaimStatus
    reason: str | None


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    player_class: str


def names_match(character: str, server_name: str) -> bool:
    """Case- and width-insensitive exact match; accents count (Hopscotch is not Höpscotch)."""

    def norm(s: str) -> str:
        return unicodedata.normalize("NFKC", s).strip().casefold()

    return bool(server_name.strip()) and norm(character) == norm(server_name)


def _target(claim: CharacterClaim) -> str:
    return f"claim {claim.id}: character {claim.character_id} ({claim.character_name})"


# --- member routes -----------------------------------------------------------------------------


@router.get("/api/characters")
async def search_characters(
    q: str = "",
    _: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[CharacterOut]:
    """Characters seen in the guild's logs whose name contains `q`, for the claim picker (REQ-HUB-CLAIM-004)."""
    found: list[Character] = await anyio.to_thread.run_sync(services.characters.search, q[:64])
    return [CharacterOut.model_validate(c) for c in found]


def _create(services: Services, principal: Principal, character_id: int) -> tuple[ClaimOut, bool]:
    name = services.characters.name_of(character_id)
    if name is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown character")
    with services.db.begin() as db:
        claim = db.scalar(select(CharacterClaim).where(CharacterClaim.character_id == character_id))
        if claim is not None and claim.status is not ClaimStatus.REJECTED:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Character already claimed")
        if claim is None:
            claim = CharacterClaim(character_id=character_id, member_id=principal.member_id, character_name=name)
            db.add(claim)
        auto = names_match(name, principal.display_name)
        claim.member_id = principal.member_id
        claim.character_name = name
        claim.raid_day_id = principal.home_day()
        claim.status = ClaimStatus.APPROVED if auto else ClaimStatus.PENDING
        claim.reason = None
        claim.decided_by = None
        claim.decided_at = datetime.now(UTC) if auto else None
        claim.created_at = datetime.now(UTC)  # a reused rejected row joins the back of the queue
        db.flush()
        if auto:
            audit.record(
                db, actor=principal.member_id, action="claim.auto_approve", target=_target(claim),
                raid_day=claim.raid_day_id, detail="character name matches server nickname",
            )  # fmt: skip
        return ClaimOut.model_validate(claim), not auto


@router.post("/api/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
    body: ClaimIn,
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    try:
        claim, needs_officer = await anyio.to_thread.run_sync(_create, services, principal, body.character_id)
    except IntegrityError:
        # Two members claimed the same unclaimed character at once; the unique constraint picked one.
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Character already claimed") from None
    # An auto-approved claim still reaches #officers as an FYI: a member could rename themselves to match someone
    # else's character first, and the officer can reassign it in one action.
    await services.notifier.notify_officers(
        {
            "kind": "claim_pending" if needs_officer else "claim_auto_approved",
            "claim_id": claim.id,
            "character": claim.character_name,
            "raid_day": claim.raid_day_id,
        }
    )
    return claim


def _own(services: Services, principal: Principal) -> list[ClaimOut]:
    with services.db() as db:
        rows = db.scalars(
            select(CharacterClaim).where(CharacterClaim.member_id == principal.member_id).order_by(CharacterClaim.id)
        )
        return [ClaimOut.model_validate(c) for c in rows]


@router.get("/api/claims")
async def my_claims(
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[ClaimOut]:
    return await anyio.to_thread.run_sync(_own, services, principal)


def _unclaim(services: Services, principal: Principal, claim_id: int) -> None:
    with services.db.begin() as db:
        claim = db.get(CharacterClaim, claim_id)
        if claim is None or claim.member_id != principal.member_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such claim")
        # REQ-HUB-PRIV-003: only the link goes; the character and its raid rows stay in wcl-store.
        audit.record(
            db, actor=principal.member_id, action="claim.unclaim", target=_target(claim), raid_day=claim.raid_day_id
        )
        db.delete(claim)


@router.delete("/api/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unclaim(
    claim_id: int,
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> None:
    await anyio.to_thread.run_sync(_unclaim, services, principal, claim_id)


# --- officer routes (scoped to the raid day in the path) ----------------------------------------


class QueuedClaimOut(ClaimOut):
    """A pending claim as an officer sees it: who is claiming, and the raid nights whose officers may decide it."""

    member_name: str
    nights: list[str]


def claim_nights(claim: CharacterClaim, member: Member | None, configured: Collection[str]) -> list[str]:
    """The raid nights whose officers decide a claim: the nights the claimant's Discord roles put them on now (their
    night Toad role, refreshed at every sign-in), else, for a member row that has never recorded its nights, the day
    recorded when they claimed. Only nights still in config count. Empty means only global officers and super admins
    decide it."""
    if member is not None and member.raid_days is not None:
        nights = list(member.raid_days)
    else:
        nights = [claim.raid_day_id] if claim.raid_day_id is not None else []
    return [n for n in nights if n in configured]


def _configured(services: Services) -> frozenset[str]:
    return frozenset(d.id for d in services.raid_days.raid_days)


def _queued(claim: CharacterClaim, member: Member | None, nights: list[str]) -> QueuedClaimOut:
    out = ClaimOut.model_validate(claim).model_dump()
    return QueuedClaimOut(
        **out, member_name=member.display_name if member else f"member {claim.member_id}", nights=nights
    )


def _pending(services: Services) -> list[tuple[CharacterClaim, Member | None, list[str]]]:
    with services.db() as db:
        rows = db.execute(
            select(CharacterClaim, Member)
            .join(Member, Member.id == CharacterClaim.member_id, isouter=True)
            .where(CharacterClaim.status == ClaimStatus.PENDING)
            .order_by(CharacterClaim.created_at, CharacterClaim.id)
        ).all()
        configured = _configured(services)
        return [(claim, member, claim_nights(claim, member, configured)) for claim, member in rows]


def _queue(services: Services, day: str) -> list[QueuedClaimOut]:
    return [_queued(c, m, nights) for c, m, nights in _pending(services) if day in nights]


@router.get("/api/days/{day}/claims")
async def claims_queue(
    day: str,
    _: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[QueuedClaimOut]:
    """The night's pending claims: those whose claimant holds this night's role (REQ-HUB-CLAIM-005)."""
    return await anyio.to_thread.run_sync(_queue, services, day)


def _unplaced(services: Services) -> list[QueuedClaimOut]:
    return [_queued(c, m, nights) for c, m, nights in _pending(services) if not nights]


@router.get("/api/admin/claims")
async def unplaced_claims(
    _: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[QueuedClaimOut]:
    """Pending claims from members who hold no raid night's role, for the global tier (REQ-HUB-CLAIM-005)."""
    return await anyio.to_thread.run_sync(_unplaced, services)


Decision = Literal["approve", "reject", "reassign"]


def _deny(
    services: Services, principal: Principal, day: str, claim_id: int, decision: str, claim_day: str | None
) -> NoReturn:
    # REQ-HUB-DAY-011: acting on a sibling day's data is refused and recorded, in its own transaction
    # so the refusal does not roll the audit row back.
    with services.db.begin() as db:
        audit.record(
            db, actor=principal.member_id, action="rbac.denied", target=f"{decision} claim {claim_id}",
            raid_day=claim_day, detail=f"via /api/days/{day}",
        )  # fmt: skip
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _decide(
    services: Services,
    principal: Principal,
    day: str | None,
    claim_id: int,
    decision: Decision,
    reason: str | None = None,
    new_member_id: int | None = None,
) -> ClaimOut:
    """Decide a claim through a night's path (`day`), or through the global tier's /api/admin path (`day` None), which
    reaches every claim."""
    with services.db.begin() as db:
        # Locked, so two officers deciding at once (the claim is on several nights' panels) get one success and a 409.
        claim = db.scalar(select(CharacterClaim).where(CharacterClaim.id == claim_id).with_for_update())
        if claim is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such claim")
        nights = claim_nights(claim, db.get(Member, claim.member_id), _configured(services))
        # Claims without a night (the claimant holds no night role) belong to the global tier.
        if day is None or day in nights:
            return _apply(db, principal, claim, decision, reason, new_member_id)
        if principal.global_officer:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim is not in this raid day")
        denied_day = nights[0] if nights else None
    _deny(services, principal, day, claim_id, decision, denied_day)


def _apply(
    db: Session,
    principal: Principal,
    claim: CharacterClaim,
    decision: Decision,
    reason: str | None,
    new_member_id: int | None,
) -> ClaimOut:
    if decision in ("approve", "reject") and claim.status is not ClaimStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Claim is not pending")
    detail: str | None = None
    if decision == "reassign":
        if new_member_id is None or db.get(Member, new_member_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such member")
        if claim.status is ClaimStatus.REJECTED:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Claim was rejected")
        detail = f"from member {claim.member_id} to member {new_member_id}"
        claim.member_id = new_member_id
        claim.status = ClaimStatus.APPROVED
    elif decision == "approve":
        claim.status = ClaimStatus.APPROVED
    else:
        detail = reason
        claim.status = ClaimStatus.REJECTED
        claim.reason = reason
    claim.decided_by = principal.member_id
    claim.decided_at = datetime.now(UTC)
    audit.record(
        db, actor=principal.member_id, action=f"claim.{decision}", target=_target(claim),
        raid_day=claim.raid_day_id, detail=detail,
    )  # fmt: skip
    db.flush()
    return ClaimOut.model_validate(claim)


@router.post("/api/days/{day}/claims/{claim_id}/approve")
async def approve_claim(
    day: str,
    claim_id: int,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, day, claim_id, "approve")


@router.post("/api/days/{day}/claims/{claim_id}/reject")
async def reject_claim(
    day: str,
    claim_id: int,
    body: RejectIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, day, claim_id, "reject", body.reason)


@router.post("/api/days/{day}/claims/{claim_id}/reassign")
async def reassign_claim(
    day: str,
    claim_id: int,
    body: ReassignIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, day, claim_id, "reassign", None, body.member_id)


# --- the global tier's decisions, for claims of every night and those with none ------------------


@router.post("/api/admin/claims/{claim_id}/approve")
async def approve_any_claim(
    claim_id: int,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, None, claim_id, "approve")


@router.post("/api/admin/claims/{claim_id}/reject")
async def reject_any_claim(
    claim_id: int,
    body: RejectIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, None, claim_id, "reject", body.reason)


@router.post("/api/admin/claims/{claim_id}/reassign")
async def reassign_any_claim(
    claim_id: int,
    body: ReassignIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> ClaimOut:
    return await anyio.to_thread.run_sync(
        _decide, services, principal, None, claim_id, "reassign", None, body.member_id
    )
