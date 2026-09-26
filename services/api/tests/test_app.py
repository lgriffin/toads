from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from hub_db import AuditEntry
from sqlalchemy import select
from toads_api.main import create_app
from toads_api.rbac import HubRole, Principal
from toads_api.rbac.deps import get_principal

from conftest import Hub


@pytest.fixture
def as_principal(hub: Hub) -> Iterator[object]:
    def _as(principal: Principal) -> TestClient:
        async def _p() -> Principal:
            return principal

        hub.app.dependency_overrides[get_principal] = _p
        return hub.client

    yield _as
    hub.app.dependency_overrides.clear()


def test_healthz(hub: Hub) -> None:
    assert hub.client.get("/healthz").json() == {"status": "ok"}


def test_openapi_served(hub: Hub) -> None:
    assert hub.client.get("/api/openapi.json").status_code == 200


def test_anonymous_gets_401(hub: Hub) -> None:
    assert hub.client.get("/api/me").status_code == 401


def test_plain_member_has_no_me_page(as_principal) -> None:
    assert as_principal(Principal(member_id=1)).get("/api/me").status_code == 403


def test_raider_sees_me(as_principal) -> None:
    r = as_principal(Principal(member_id=7, day_roles={"wed": HubRole.RAIDER})).get("/api/me")
    assert r.json() == {"member_id": 7}


def test_sibling_day_officer_denied_and_audited(hub: Hub, as_principal) -> None:
    c = as_principal(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}))
    assert c.post("/api/days/wed/admin/sync").status_code == 202
    assert c.post("/api/days/sun/admin/sync").status_code == 403
    with hub.db() as db:
        rows = [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert rows == [("sync.trigger", "wed"), ("rbac.denied", "sun")]


def test_non_officer_denial_is_not_audited(hub: Hub, as_principal) -> None:
    c = as_principal(Principal(member_id=1, day_roles={"wed": HubRole.RAIDER}))
    assert c.post("/api/days/wed/admin/sync").status_code == 403
    with hub.db() as db:
        assert db.scalars(select(AuditEntry)).all() == []


def test_unknown_raid_day_is_404(as_principal) -> None:
    c = as_principal(Principal(member_id=1, global_officer=True))
    assert c.post("/api/days/fri/admin/sync").status_code == 404


@pytest.mark.security
def test_day_in_body_or_query_is_ignored(as_principal) -> None:
    c = as_principal(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}))
    assert c.post("/api/days/sun/admin/sync?day=wed", json={"day": "wed"}).status_code == 403


def test_routes_need_the_lifespan() -> None:
    with pytest.raises(RuntimeError, match="lifespan"):
        TestClient(create_app()).get("/api/session")


@pytest.mark.security
def test_validation_errors_do_not_echo_input() -> None:
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from pydantic import BaseModel
    from toads_api.main import _validation_error

    class Body(BaseModel):
        n: int

    app = FastAPI()
    app.add_exception_handler(RequestValidationError, _validation_error)

    @app.post("/x")
    async def x(body: Body) -> int:
        return body.n

    r = TestClient(app).post("/x", json={"n": "planted-secret-value"})
    assert r.status_code == 422
    assert "planted-secret-value" not in r.text
