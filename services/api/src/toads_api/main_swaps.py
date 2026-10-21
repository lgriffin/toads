"""A member's main character and their requests to swap it (REQ-HUB-CLAIM-006, REQ-HUB-ME-006, docs/me.md).

Me opens on the member's main: the alt officers approved as main while they still hold it, else their first approved
claim. Making another approved character the main is a request that waits, like a claim, for an officer of the
member's raid nights (their night roles now, else the day recorded when they asked); members on no night go to the
global tier's /api/admin/main-swaps. Officer routes take the raid day from the path only, and a request outside that
night is refused with 403 and an audit row.

- GET    /api/me/main                                   the caller's main, their other approved characters, any request
- POST   /api/me/main                                   ask to make one of their approved alts their main
- DELETE /api/me/main/request                           withdraw the pending ask
- GET    /api/days/{day}/main-swaps                     the night's pending asks
- POST   /api/days/{day}/main-swaps/{swap_id}/approve|reject
- GET    /api/admin/main-swaps                          pending asks from members on no night (global tier)
- POST   /api/admin/main-swaps/{swap_id}/approve|reject any night's, for the global tier
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, NoReturn

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from hub_db import CharacterClaim, ClaimStatus, MainSwapRequest, Member, main_claim
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from toads_api import audit
from toads_api.claims import RejectIn, configured_nights, member_nights
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

router = APIRouter()


class MainIn(BaseModel):
    character_id: int = Field(gt=0)


class CharacterRef(BaseModel):
    character_id: int
    character_name: str


class SwapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    character_id: int
    character_name: str
    raid_day_id: str | None
    status: ClaimStatus
    reason: str | None


class MyMainOut(BaseModel):
    # None until the member holds an approved claim.
    main: CharacterRef | None
    # Their other approved characters, by name: the ones they may ask to make their main.
    alts: list[CharacterRef]
    # Their latest ask: pending, or the last decided one so Me can say how it went. None when they never asked or
    # the decided ask is no longer news (they swapped since, or the character left them).
    request: SwapOut | None


def _approved(db: Session, member_id: int) -> list[CharacterClaim]:
    return list(
        db.scalars(
            select(CharacterClaim)
            .where(CharacterClaim.member_id == member_id, CharacterClaim.status == ClaimStatus.APPROVED)
            .order_by(CharacterClaim.id)
        )
    )


def _latest(db: Session, member_id: int) -> MainSwapRequest | None:
    return db.scalar(
        select(MainSwapRequest)
        .where(MainSwapRequest.member_id == member_id)
        .order_by(MainSwapRequest.id.desc())
        .limit(1)
    )


def _pending_of(db: Session, member_id: int) -> MainSwapRequest | None:
    """The member's pending ask, locked as an officer's decision locks it, so an ask or a withdrawal never edits or
    deletes a row an officer decided meanwhile: the row is re-read under the lock and no longer matches once decided."""
    return db.scalar(
        select(MainSwapRequest)
        .where(MainSwapRequest.member_id == member_id, MainSwapRequest.status == ClaimStatus.PENDING)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _ref(claim: CharacterClaim) -> CharacterRef:
    return CharacterRef(character_id=claim.character_id, character_name=claim.character_name)


def _mine(services: Services, principal: Principal) -> MyMainOut:
    with services.db() as db:
        member = db.get(Member, principal.member_id)
        approved = _approved(db, principal.member_id)
        main = main_claim(member.main_character_id if member else None, approved)
        alts = sorted((c for c in approved if c is not main), key=lambda c: c.character_name.casefold())
        latest = _latest(db, principal.member_id)
        # A decided ask stays news only while it still says something about the alts they hold.
        held = {c.character_id for c in alts}
        if latest is not None and latest.status is not ClaimStatus.PENDING and latest.character_id not in held:
            latest = None
        return MyMainOut(
            main=_ref(main) if main else None,
            alts=[_ref(c) for c in alts],
            request=SwapOut.model_validate(latest) if latest else None,
        )


@router.get("/api/me/main")
async def my_main(
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> MyMainOut:
    return await anyio.to_thread.run_sync(_mine, services, principal)


def _ask(services: Services, principal: Principal, character_id: int) -> SwapOut:
    with services.db.begin() as db:
        # Locked, so two asks at once from the same member leave one pending row.
        member = db.scalar(select(Member).where(Member.id == principal.member_id).with_for_update())
        if member is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown member")
        approved = _approved(db, member.id)
        wanted = next((c for c in approved if c.character_id == character_id), None)
        if wanted is None:
            # Only approved claims: a free choice would let anyone raid as someone else's character.
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Choose one of your approved characters")
        if main_claim(member.main_character_id, approved) is wanted:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="That character is already your main")
        # A new ask makes earlier rejections old news; the audit log keeps them.
        db.execute(
            delete(MainSwapRequest).where(
                MainSwapRequest.member_id == member.id, MainSwapRequest.status == ClaimStatus.REJECTED
            )
        )
        swap = _pending_of(db, member.id)
        if swap is None:
            swap = MainSwapRequest(member_id=member.id)
            db.add(swap)
        swap.character_id = wanted.character_id
        swap.character_name = wanted.character_name
        swap.raid_day_id = principal.home_day()
        swap.status = ClaimStatus.PENDING
        swap.created_at = datetime.now(UTC)  # a changed ask joins the back of the queue
        db.flush()
        audit.record(
            db, actor=member.id, action="main.request", target=_target(swap), raid_day=swap.raid_day_id
        )  # fmt: skip
        return SwapOut.model_validate(swap)


@router.post("/api/me/main", status_code=status.HTTP_201_CREATED)
async def ask_for_main(
    body: MainIn,
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> SwapOut:
    swap = await anyio.to_thread.run_sync(_ask, services, principal, body.character_id)
    await services.notifier.notify_officers(
        {
            "kind": "main_swap_pending",
            "swap_id": swap.id,
            "character": swap.character_name,
            "raid_day": swap.raid_day_id,
        }
    )
    return swap


def _withdraw(services: Services, principal: Principal) -> None:
    with services.db.begin() as db:
        swap = _pending_of(db, principal.member_id)
        if swap is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No main swap is waiting")
        audit.record(
            db, actor=principal.member_id, action="main.withdraw", target=_target(swap), raid_day=swap.raid_day_id
        )
        db.delete(swap)


@router.delete("/api/me/main/request", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_main_request(
    principal: Principal = Depends(require(Permission.CLAIM_CHARACTER)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> None:
    await anyio.to_thread.run_sync(_withdraw, services, principal)


# --- officer routes (scoped to the raid day in the path) ----------------------------------------


class QueuedSwapOut(SwapOut):
    """A pending ask as an officer sees it: who is asking, their main now, and the nights whose officers decide it."""

    member_name: str
    current_main: str | None
    nights: list[str]


def _target(swap: MainSwapRequest) -> str:
    return f"main swap {swap.id}: member {swap.member_id} to character {swap.character_id} ({swap.character_name})"


def _pending(services: Services) -> list[QueuedSwapOut]:
    configured = configured_nights(services)
    with services.db() as db:
        rows = db.execute(
            select(MainSwapRequest, Member)
            .join(Member, Member.id == MainSwapRequest.member_id, isouter=True)
            .where(MainSwapRequest.status == ClaimStatus.PENDING)
            .order_by(MainSwapRequest.created_at, MainSwapRequest.id)
        ).all()
        out = []
        for swap, member in rows:
            main = main_claim(member.main_character_id if member else None, _approved(db, swap.member_id))
            out.append(
                QueuedSwapOut(
                    **SwapOut.model_validate(swap).model_dump(),
                    member_name=member.display_name if member else f"member {swap.member_id}",
                    current_main=main.character_name if main else None,
                    nights=member_nights(member, swap.raid_day_id, configured),
                )
            )
        return out


@router.get("/api/days/{day}/main-swaps")
async def main_swaps_queue(
    day: str,
    _: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[QueuedSwapOut]:
    """The night's pending main swaps: those whose member holds this night's role (REQ-HUB-CLAIM-006)."""
    return [s for s in await anyio.to_thread.run_sync(_pending, services) if day in s.nights]


@router.get("/api/admin/main-swaps")
async def unplaced_main_swaps(
    _: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[QueuedSwapOut]:
    """Pending main swaps from members who hold no raid night's role, for the global tier."""
    return [s for s in await anyio.to_thread.run_sync(_pending, services) if not s.nights]


Decision = Literal["approve", "reject"]


def _deny(
    services: Services, principal: Principal, day: str, swap_id: int, decision: str, night: str | None
) -> NoReturn:
    # REQ-HUB-DAY-011: acting on a sibling day's data is refused and recorded, in its own transaction.
    with services.db.begin() as db:
        audit.record(
            db, actor=principal.member_id, action="rbac.denied", target=f"{decision} main swap {swap_id}",
            raid_day=night, detail=f"via /api/days/{day}",
        )  # fmt: skip
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _decide(
    services: Services, principal: Principal, day: str | None, swap_id: int, decision: Decision, reason: str | None
) -> SwapOut:
    with services.db.begin() as db:
        # Locked, so two officers deciding at once (the ask is on several nights' panels) get one success and a 409.
        swap = db.scalar(select(MainSwapRequest).where(MainSwapRequest.id == swap_id).with_for_update())
        if swap is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such main swap")
        member = db.get(Member, swap.member_id)
        nights = member_nights(member, swap.raid_day_id, configured_nights(services))
        if day is None or day in nights:
            return _apply(db, principal, swap, member, decision, reason)
        if principal.global_officer:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Main swap is not in this raid day")
        denied_day = nights[0] if nights else None
    _deny(services, principal, day, swap_id, decision, denied_day)


def _apply(
    db: Session,
    principal: Principal,
    swap: MainSwapRequest,
    member: Member | None,
    decision: Decision,
    reason: str | None,
) -> SwapOut:
    if swap.status is not ClaimStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Main swap is not pending")
    if decision == "approve":
        held = member is not None and any(c.character_id == swap.character_id for c in _approved(db, member.id))
        if member is None or not held:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="They no longer hold that character")
        member.main_character_id = swap.character_id
        swap.status = ClaimStatus.APPROVED
    else:
        swap.status = ClaimStatus.REJECTED
        swap.reason = reason
    swap.decided_by = principal.member_id
    swap.decided_at = datetime.now(UTC)
    audit.record(
        db, actor=principal.member_id, action=f"main.{decision}", target=_target(swap),
        raid_day=swap.raid_day_id, detail=reason,
    )  # fmt: skip
    db.flush()
    return SwapOut.model_validate(swap)


@router.post("/api/days/{day}/main-swaps/{swap_id}/approve")
async def approve_main_swap(
    day: str,
    swap_id: int,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> SwapOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, day, swap_id, "approve", None)


@router.post("/api/days/{day}/main-swaps/{swap_id}/reject")
async def reject_main_swap(
    day: str,
    swap_id: int,
    body: RejectIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS, scoped=True)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> SwapOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, day, swap_id, "reject", body.reason)


@router.post("/api/admin/main-swaps/{swap_id}/approve")
async def approve_any_main_swap(
    swap_id: int,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> SwapOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, None, swap_id, "approve", None)


@router.post("/api/admin/main-swaps/{swap_id}/reject")
async def reject_any_main_swap(
    swap_id: int,
    body: RejectIn,
    principal: Principal = Depends(require(Permission.APPROVE_CLAIMS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> SwapOut:
    return await anyio.to_thread.run_sync(_decide, services, principal, None, swap_id, "reject", body.reason)
