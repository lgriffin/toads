import pytest
from fastapi.testclient import TestClient
from toads_api.main import create_app
from toads_api.rbac import HubRole, Principal
from toads_api.rbac.deps import get_principal


def client_as(principal: Principal | None) -> TestClient:
    app = create_app()
    if principal is not None:

        async def _p() -> Principal:
            return principal

        app.dependency_overrides[get_principal] = _p
    return TestClient(app)


def test_healthz() -> None:
    assert client_as(None).get("/healthz").json() == {"status": "ok"}


def test_openapi_served() -> None:
    assert client_as(None).get("/api/openapi.json").status_code == 200


def test_anonymous_gets_401() -> None:
    assert client_as(None).get("/api/me").status_code == 401


def test_plain_member_has_no_me_page() -> None:
    assert client_as(Principal(member_id=1)).get("/api/me").status_code == 403


def test_raider_sees_me() -> None:
    r = client_as(Principal(member_id=7, day_roles={"wed": HubRole.RAIDER})).get("/api/me")
    assert r.json() == {"member_id": 7}


def test_sibling_day_officer_denied() -> None:
    c = client_as(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}))
    assert c.post("/api/days/wed/admin/sync").status_code == 202
    assert c.post("/api/days/sun/admin/sync").status_code == 403


@pytest.mark.security
def test_day_in_body_or_query_is_ignored() -> None:
    c = client_as(Principal(member_id=1, day_roles={"wed": HubRole.OFFICER}))
    assert c.post("/api/days/sun/admin/sync?day=wed", json={"day": "wed"}).status_code == 403


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
