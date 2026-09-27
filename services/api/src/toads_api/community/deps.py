"""Adapter wiring for the community routes: building the service, turning a Principal into what the rules need,
and the tier checks. RBAC decisions live here and in `routes.py`, never in `service.py`."""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, Request, status

from toads_api.community import recruitment
from toads_api.community.schemas import ApplicationTransition, CurationDecision, PostCreate, Visibility
from toads_api.community.service import Audience, CommunityService
from toads_api.rbac import HubRole, Principal
from toads_api.rbac.deps import get_services
from toads_api.services import Services


def get_service(request: Request) -> CommunityService:
    return get_services(request).community


async def require_service(
    authorization: str = Header(default=""),
    services: Services = Depends(get_services),  # noqa: B008
) -> None:
    """The bot authenticates with `Authorization: Bearer <service token>`, compared in constant time."""
    scheme, _, token = authorization.partition(" ")
    expected = services.settings.hub_service_token.get_secret_value()
    if (
        scheme.lower() != "bearer"
        or not token
        or not expected
        or not hmac.compare_digest(token.encode(), expected.encode())
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not the bot")


# ------------------------------------------------------------ principal -> data


def audience_of(principal: Principal) -> Audience:
    if principal.global_officer:
        return Audience(signed_in=True, days=None)
    return Audience(signed_in=True, days=frozenset(d for d, r in principal.day_roles.items() if r > HubRole.MEMBER))


def officer_scopes(principal: Principal) -> list[str | None]:
    """The scopes an officer leads: [None] (everything) for the global tier, else their own raid days."""
    if principal.global_officer:
        return [None]
    return [d for d, role in principal.day_roles.items() if role is HubRole.OFFICER]


def scope_of(request: Request) -> str | None:
    """The raid day a route works in: from the path only (REQ-HUB-DAY-023); None on guild-wide routes."""
    day = request.path_params.get("day")
    return str(day) if day is not None else None


# ------------------------------------------------------------------ tier checks

_PUBLIC_IS_GLOBAL = "Only the global tier posts to the public story"


async def post_audience_allowed(request: Request, body: PostCreate) -> None:
    """Raid-day officers write for their day; only the global routes (global officers) reach the public story."""
    if scope_of(request) is not None and body.visibility is Visibility.PUBLIC:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_PUBLIC_IS_GLOBAL)


async def curation_audience_allowed(request: Request, body: CurationDecision) -> None:
    if scope_of(request) is not None and body.visibility is Visibility.PUBLIC:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_PUBLIC_IS_GLOBAL)


async def officer_transition_allowed(body: ApplicationTransition) -> None:
    """Withdrawing is the applicant's own act; officers decline instead."""
    if body.to in recruitment.APPLICANT_ONLY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the applicant can withdraw")
