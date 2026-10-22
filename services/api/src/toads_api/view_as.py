"""View as (docs/admin.md "View as"): a super admin sees the hub as one raid night's raider or officer, to check what
those members see. Read only: while it is on, every change is refused except going back. It lives in the super admin's
server-side session, so it ends when they go back, sign out or the session expires.

- PUT    /api/admin/view-as/{as_tier}/{night}   view the hub as that night's raider or officer
- DELETE /api/admin/view-as                     go back to being a super admin
"""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Any, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status

from toads_api import audit
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services
from toads_api.sessions import SESSION_COOKIE, SessionData

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/admin/view-as", tags=["super admins"])

Live = Annotated[Services, Depends(get_services)]
SuperAdmin = Annotated[Principal, Depends(require(Permission.VIEW_AS))]


async def _session(request: Request, live: Services) -> tuple[str, SessionData]:
    """The caller's own session; a bot acting for a member has none to change."""
    session_id = request.cookies.get(SESSION_COOKIE)
    data = await live.sessions.get(session_id) if session_id else None
    if session_id is None or data is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="View as needs a signed-in session")
    return session_id, data


def _record(live: Services, principal: Principal, action: str, target: str, raid_day: str | None) -> None:
    with live.db.begin() as db:
        audit.record(db, actor=principal.member_id, action=action, target=target, raid_day=raid_day)


@router.put("/{as_tier}/{night}")
async def start_viewing_as(
    as_tier: Literal["raider", "officer"],
    night: Annotated[str, Path(pattern=r"^[a-z0-9_-]{1,32}$")],
    request: Request,
    principal: SuperAdmin,
    live: Live,
) -> dict[str, Any]:
    """View the hub as `night`'s raider or officer until going back. Switching from one view to another is allowed."""
    day = live.raid_days.day(night)
    if day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown raid day")
    session_id, data = await _session(request, live)
    # Audited first, so no view starts or ends without its entry.
    await anyio.to_thread.run_sync(_record, live, principal, "view_as.start", as_tier, night)
    await live.sessions.save(session_id, replace(data, view_as_role=as_tier, view_as_day=night))
    log.info("view_as.start", member_id=principal.member_id, role=as_tier, raid_day=night)
    return {"role": as_tier, "raid_day": night, "name": day.name}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def stop_viewing_as(request: Request, principal: SuperAdmin, live: Live) -> Response:
    """Go back to being a super admin; doing so when not viewing as anyone is harmless."""
    session_id, data = await _session(request, live)
    if data.view_as_role or data.view_as_day:
        await anyio.to_thread.run_sync(_record, live, principal, "view_as.end", data.view_as_role, data.view_as_day)
        await live.sessions.save(session_id, replace(data, view_as_role="", view_as_day=""))
        log.info("view_as.end", member_id=principal.member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
