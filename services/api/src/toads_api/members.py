"""Members directory (REQ-HUB-PRIV-004): everyone who has signed in to the hub.

Every signed-in member sees display names; Discord user ids go to officers only (global or any raid
day). Ids are strings because Discord snowflakes do not fit a JavaScript number.
"""

from __future__ import annotations

import anyio
from fastapi import APIRouter, Depends
from hub_db import Member
from pydantic import BaseModel
from sqlalchemy import select

from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

router = APIRouter()


class MemberOut(BaseModel):
    member_id: int
    display_name: str
    discord_user_id: str | None


def _list(services: Services, with_discord_ids: bool) -> list[MemberOut]:
    with services.db() as db:
        rows = db.scalars(select(Member).order_by(Member.display_name, Member.id))
        return [
            MemberOut(
                member_id=m.id,
                display_name=m.display_name,
                discord_user_id=str(m.discord_user_id) if with_discord_ids else None,
            )
            for m in rows
        ]


@router.get("/api/members")
async def list_members(
    principal: Principal = Depends(require(Permission.VIEW_GUILD_RAIDS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> list[MemberOut]:
    return await anyio.to_thread.run_sync(_list, services, principal.is_officer)
