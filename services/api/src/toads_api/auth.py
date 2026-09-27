"""Discord OAuth2 authorization-code + PKCE login (REQ-HUB-AUTH-001/002).

/auth/login stores a random state and PKCE verifier in Redis under a random id held in a short-lived
HttpOnly cookie scoped to /auth. /auth/callback takes that record atomically (single use, so a
replayed state is refused), checks the state, exchanges the code with the verifier, and creates a
server-side session only for members of the Toads server.
"""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
from typing import Any
from urllib.parse import urlencode

import anyio
import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from hub_db import Member
from sqlalchemy import select

from toads_api.discord_api import SCOPES, DiscordAuthError, DiscordError, GuildMember
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import HubRole, Permission, Principal
from toads_api.services import Services
from toads_api.sessions import LOGIN_COOKIE, SESSION_COOKIE, PendingLogin, SessionData

log = structlog.get_logger(__name__)
router = APIRouter()

MEMBERS_ONLY_PATH = "/members-only"


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _cookie(response: Response, name: str, value: str, *, max_age: int, path: str) -> None:
    response.set_cookie(name, value, max_age=max_age, path=path, httponly=True, secure=True, samesite="lax")


def _clear_cookie(response: Response, name: str, *, path: str) -> None:
    response.delete_cookie(name, path=path, httponly=True, secure=True, samesite="lax")


def _failed(message: str, code: int = status.HTTP_400_BAD_REQUEST) -> HTMLResponse:
    body = (
        "<!doctype html><meta charset=utf-8><title>Sign-in failed</title>"
        f"<p>{html.escape(message)}</p><p><a href=/auth/login>Try again</a></p>"
    )
    response = HTMLResponse(body, status_code=code)
    _clear_cookie(response, LOGIN_COOKIE, path="/auth")
    return response


def _upsert_member(services: Services, member: GuildMember) -> int:
    with services.db.begin() as db:
        row = db.scalar(select(Member).where(Member.discord_user_id == member.user_id))
        if row is None:
            row = Member(discord_user_id=member.user_id, display_name=member.server_name)
            db.add(row)
            db.flush()
        else:
            row.display_name = member.server_name
        return row.id


@router.get("/auth/login", include_in_schema=False)
async def login(services: Services = Depends(get_services)) -> Response:  # noqa: B008
    settings = services.settings
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    login_id = await services.sessions.begin_login(PendingLogin(state=state, code_verifier=verifier))
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.discord_client_id,
            "redirect_uri": settings.discord_redirect_uri,
            "scope": SCOPES,
            "state": state,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    response = RedirectResponse(f"{settings.discord_authorize_url}?{query}", status_code=status.HTTP_302_FOUND)
    _cookie(response, LOGIN_COOKIE, login_id, max_age=settings.login_ttl_seconds, path="/auth")
    return response


@router.get("/auth/callback", include_in_schema=False)
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    services: Services = Depends(get_services),  # noqa: B008
) -> Response:
    login_id = request.cookies.get(LOGIN_COOKIE)
    pending = await services.sessions.take_login(login_id) if login_id else None
    if pending is None or state is None or not secrets.compare_digest(state.encode(), pending.state.encode()):
        log.info("auth.callback_refused", reason="state")
        return _failed("This sign-in link has expired or was already used.")
    if not code:
        return _failed("Sign-in was cancelled.")
    try:
        token = await services.discord.exchange_code(code, pending.code_verifier)
        member = await services.discord.current_member(token)
    except DiscordAuthError:
        log.info("auth.callback_refused", reason="discord_rejected")
        return _failed("Discord did not accept this sign-in.")
    except DiscordError:
        log.warning("auth.discord_unavailable")
        return _failed("Discord is not answering; try again shortly.", status.HTTP_502_BAD_GATEWAY)

    public = services.settings.public_base_url.rstrip("/")
    if member is None:
        # REQ-HUB-AUTH-002: no member row, no session.
        response: Response = RedirectResponse(f"{public}{MEMBERS_ONLY_PATH}", status_code=status.HTTP_303_SEE_OTHER)
        _clear_cookie(response, LOGIN_COOKIE, path="/auth")
        return response

    # Never reuse a session id the browser already had (session fixation).
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        await services.sessions.delete(old)
    member_id = await anyio.to_thread.run_sync(_upsert_member, services, member)
    session_id = await services.sessions.create(
        SessionData(
            member_id=member_id,
            discord_user_id=member.user_id,
            display_name=member.server_name,
            role_ids=sorted(member.role_ids),
            access_token=token,
            refreshed_at=services.clock(),
        )
    )
    log.info("auth.signed_in", member_id=member_id)
    response = RedirectResponse(f"{public}/", status_code=status.HTTP_303_SEE_OTHER)
    _clear_cookie(response, LOGIN_COOKIE, path="/auth")
    _cookie(response, SESSION_COOKIE, session_id, max_age=services.settings.session_ttl_seconds, path="/")
    return response


@router.post("/auth/logout", include_in_schema=False)
async def logout(request: Request, services: Services = Depends(get_services)) -> Response:  # noqa: B008
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        await services.sessions.delete(session_id)
    response = RedirectResponse(
        f"{services.settings.public_base_url.rstrip('/')}/", status_code=status.HTTP_303_SEE_OTHER
    )
    _clear_cookie(response, SESSION_COOKIE, path="/")
    return response


@router.get("/api/session")
async def session_info(
    principal: Principal = Depends(require(Permission.VIEW_GUILD_RAIDS)),  # noqa: B008
    services: Services = Depends(get_services),  # noqa: B008
) -> dict[str, Any]:
    """Who is signed in and their standing per raid day (REQ-HUB-DAY-004), for the web app and community pages.

    raid_days: days the member holds a trial, raider or officer role on, in config order.
    officer_days: days they hold officer powers for; every configured day for a global officer.
    """
    days = [d.id for d in services.raid_days.raid_days]
    # The name the member chose to be shown by (REQ-HUB-PRIV-005). The principal keeps the Discord nickname, which
    # claim auto-approval compares against.
    names = await anyio.to_thread.run_sync(services.account.shown_names, [principal.member_id])
    return {
        "member_id": principal.member_id,
        "display_name": names.get(principal.member_id, principal.display_name),
        "global_officer": principal.global_officer,
        "day_roles": {day: role.name.lower() for day, role in principal.day_roles.items()},
        "raid_days": [d for d in days if d in principal.day_roles],
        "officer_days": [d for d in days if principal.global_officer or principal.day_roles.get(d) is HubRole.OFFICER],
    }
