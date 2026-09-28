"""Reference comparison jobs: import another guild's report, compare one of our raids with it, relabel or delete it.

Officers queue these through the API (toads_api.reference); RQ runs `run_reference_job(job_id)`. The job reads its
request from hub-db, does the work with wcl-app's ReferenceService on the analyzer's Postgres tables, records the
outcome on the job, and republishes the lists of stored raids the officer page picks from.

Reading another guild's report needs the dedicated login: the guild's Warcraft Logs account an officer connected.
Its token lives encrypted in hub-db; the job refreshes it when it has expired and stores the refreshed one. When
Warcraft Logs refuses to refresh it, the login is marked expired and the officer page asks for a new sign-in.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import cache
from typing import Any

import structlog
from hub_db import CredentialCipher, CredentialDecryptError
from hub_db.reference import (
    JobKind,
    JobStatus,
    LoginToken,
    delete_comparisons_of,
    load_login,
    mark_login_expired,
    save_comparison,
    save_page,
    store_refreshed_login,
    update_job,
)
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from wcl_app import AppContext, ReferenceAuthRequired, ReferenceRequestError, ReferenceService
from wcl_app.context import StorageFactory
from wcl_core.client import WarcraftLogsClient
from wcl_core.common.errors import AuthenticationError, WarcraftLogsError
from wcl_core.user_auth import HostedUserToken, UserToken, token_url_for, user_api_url
from wcl_store import StorageError

from toads_worker import store
from toads_worker.settings import Settings
from toads_worker.wcl_keys import client_for

log = structlog.get_logger(__name__)

# How many stored raids the officer page offers to pick from.
MAX_REFERENCES = 200
MAX_GUILD_RAIDS = 100

EXPIRED_MESSAGE = "The Warcraft Logs sign-in has expired; connect the account again."
NO_LOGIN_MESSAGE = "Connect the Warcraft Logs account before importing a reference."


class LoginExpired(AuthenticationError):
    """Warcraft Logs refused to refresh the dedicated login's token."""


@cache
def _sessions(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(create_engine(database_url, pool_pre_ping=True), expire_on_commit=False)


def hub_sessions(settings: Settings) -> sessionmaker[Session]:
    return _sessions(settings.database_url.get_secret_value())


class DedicatedLogin:
    """The dedicated login's token in hub-db, as wcl-core's UserToken."""

    def __init__(self, db: sessionmaker[Session], cipher: CredentialCipher) -> None:
        self._db = db
        self._cipher = cipher

    def token(self) -> UserToken | None:
        with self._db() as db:
            try:
                stored = load_login(db, self._cipher)
            except CredentialDecryptError:
                log.warning("reference.login_unreadable")
                return None
        if stored is None:
            return None
        refresh = SecretStr(stored.refresh_token) if stored.refresh_token else None
        return UserToken(SecretStr(stored.access_token), refresh, stored.expires_at)

    def save(self, token: UserToken) -> None:
        refresh = token.refresh_token.get_secret_value() if token.refresh_token else None
        with self._db.begin() as db:
            store_refreshed_login(
                db, self._cipher, LoginToken(token.access_token.get_secret_value(), refresh, token.expires_at)
            )

    def expire(self) -> None:
        with self._db.begin() as db:
            mark_login_expired(db)


class _LoginTokens:
    """HostedUserToken whose refusal to refresh reads as LoginExpired, so it is never mistaken for the guild key."""

    def __init__(self, tokens: HostedUserToken) -> None:
        self._tokens = tokens

    def get_token(self) -> str:
        try:
            return self._tokens.get_token()
        except AuthenticationError as exc:
            raise LoginExpired(str(exc)) from exc


def user_client_factory(settings: Settings, login: DedicatedLogin) -> Callable[[], WarcraftLogsClient | None]:
    """AppContext's `user_client`: a client on the dedicated login, or None when nobody has connected it."""

    def make() -> WarcraftLogsClient | None:
        token = login.token()
        if token is None:
            return None
        tokens = HostedUserToken(
            token,
            settings.wcl_client_id,
            settings.wcl_client_secret,
            token_url_for(settings.wcl_api_url),
            on_refresh=login.save,
        )
        client = WarcraftLogsClient(
            _LoginTokens(tokens), cache_enabled=False, api_url=user_api_url(settings.wcl_api_url)
        )
        client.MIN_REQUEST_INTERVAL = settings.wcl_throttle_ms / 1000
        client.MAX_RETRIES = settings.wcl_max_retries
        return client

    return make


def _stamp() -> str:
    """The analyzer's local-time format, which sorts as text."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def publish_page(refs: ReferenceService, db: sessionmaker[Session]) -> dict[str, int]:
    """Store the lists of reference and guild raids the officer page picks from."""
    references = [r.to_dict() for r in refs.references(MAX_REFERENCES)]
    guild_raids = [r.to_dict() for r in refs.guild_raids(MAX_GUILD_RAIDS)]
    with db.begin() as s:
        save_page(s, _stamp(), references, guild_raids)
    return {"references": len(references), "guild_raids": len(guild_raids)}


def _run(kind: str, params: dict[str, Any], refs: ReferenceService, db: sessionmaker[Session]) -> str:
    """Carry out one request; returns the message the officer sees."""
    if kind == JobKind.IMPORT:
        analysis = refs.import_reference(str(params["report"]), label=params.get("label"))
        return f"Imported {analysis.metadata.title}."
    if kind == JobKind.COMPARE:
        comparison = refs.compare(str(params["guild_report"]), str(params["reference_report"]))
        with db.begin() as s:
            save_comparison(s, comparison.to_dict(), _stamp())
        return f"Compared {comparison.guild.title} with {comparison.reference.title}."
    if kind == JobKind.LABEL:
        refs.set_label(str(params["report"]), params.get("label"))
        return "Label saved." if params.get("label") else "Label cleared."
    if kind == JobKind.DELETE:
        code = str(params["report"])
        refs.delete_reference(code)
        with db.begin() as s:
            delete_comparisons_of(s, code)
        return "Reference deleted."
    raise ReferenceRequestError(f"Unknown request {kind!r}")


def _outcome(
    kind: str, params: dict[str, Any], refs: ReferenceService, db: sessionmaker[Session]
) -> tuple[JobStatus, str]:
    try:
        return JobStatus.DONE, _run(kind, params, refs, db)
    except ReferenceRequestError as exc:
        return JobStatus.FAILED, str(exc)
    except ReferenceAuthRequired:
        return JobStatus.FAILED, NO_LOGIN_MESSAGE
    except LoginExpired:
        return JobStatus.FAILED, EXPIRED_MESSAGE
    except (WarcraftLogsError, StorageError, OSError) as exc:
        # requests' errors are OSErrors. Only the kind of failure reaches the officer; the detail goes to the log.
        log.warning("reference.job_failed", kind=kind, error=type(exc).__name__)
        return JobStatus.FAILED, "Warcraft Logs or the database failed; try again shortly."


def run_reference_job(
    job_id: str,
    *,
    settings: Settings | None = None,
    storage: StorageFactory | None = None,
    db: sessionmaker[Session] | None = None,
    client: WarcraftLogsClient | None = None,
) -> dict[str, Any]:
    """Run the queued request `job_id`. Returns its outcome (RQ keeps it as the job result)."""
    settings = settings or Settings()
    db = db or hub_sessions(settings)
    with db.begin() as s:
        job = update_job(s, job_id, JobStatus.RUNNING)
        if job is None:
            return {"job": job_id, "status": "missing"}
        kind, params = job.kind, dict(job.params)

    login = DedicatedLogin(db, CredentialCipher.from_setting(settings.credentials_keys.get_secret_value()))
    ctx = AppContext.headless(
        client if client is not None else client_for(settings),
        storage if storage is not None else store.storage(settings),
        user_client=user_client_factory(settings, login),
    )
    refs = ReferenceService(ctx)
    status, message = _outcome(kind, params, refs, db)
    if message == EXPIRED_MESSAGE:
        login.expire()
    with db.begin() as s:
        update_job(s, job_id, status, message)
    log.info("reference.job_finished", kind=kind, status=status.value)
    try:
        publish_page(refs, db)
    except StorageError:
        log.warning("reference.page_not_published")
    return {"job": job_id, "status": status.value, "message": message}


def publish_reference_page(
    settings: Settings | None = None, *, storage: StorageFactory | None = None
) -> dict[str, int]:
    """`toads-worker publish-reference`: refresh the raid lists, e.g. after the nightly sync stored new raids."""
    settings = settings or Settings()
    ctx = AppContext.headless(client_for(settings), storage if storage is not None else store.storage(settings))
    return publish_page(ReferenceService(ctx), hub_sessions(settings))
