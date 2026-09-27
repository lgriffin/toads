"""Every string input at the community API boundary is fuzzed: a bad input is a 4xx, never a 500 or an echo."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from toads_api.community.demo import ANNOUNCEMENTS, PRINCIPALS, demo_service

from conftest import community_client

pytestmark = pytest.mark.security

TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
text = st.text(max_size=1200)


def _client(who: str) -> TestClient:
    store = demo_service(lambda: datetime(2026, 9, 26, tzinfo=UTC))
    return community_client(store, PRINCIPALS[who], raise_server_exceptions=False)


FUZZ = settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@FUZZ
@given(
    st.fixed_dictionaries(
        {
            "character_name": text,
            "class_name": text,
            "spec": text,
            "role": st.sampled_from(["Tank", "Healer", "Melee", "Ranged"]) | text,
            "raid_days": st.lists(text, max_size=3),
            "experience": text,
            "availability": text,
            "logs_url": st.none() | text,
        }
    )
)
def test_applications(body: dict[str, Any]) -> None:
    r = _client("applicant").post("/api/applications", json=body)
    assert r.status_code in {201, 409, 422}
    if r.status_code == 422:
        for value in (body["experience"], body["character_name"]):
            if len(value) >= 8:
                assert value not in r.text


@FUZZ
@given(st.fixed_dictionaries({"title": text, "body": text, "visibility": st.sampled_from(["public", "guild"]) | text}))
def test_posts(body: dict[str, Any]) -> None:
    assert _client("global officer").post("/api/admin/posts", json=body).status_code in {201, 422}


@FUZZ
@given(st.fixed_dictionaries({"title": text, "url": text, "boss": st.none() | text, "raid_id": st.none() | text}))
def test_highlights(body: dict[str, Any]) -> None:
    assert _client("Wednesday raider").post("/api/highlights", json=body).status_code in {201, 422}


@FUZZ
@given(st.fixed_dictionaries({"author_name": text, "content": st.text(max_size=4500)}))
def test_discord_messages(fields: dict[str, Any]) -> None:
    body = {"channel_id": ANNOUNCEMENTS, "message_id": 1, "created_at": "2026-09-26T17:00:00Z", **fields}
    r = _client("applicant").post("/api/bot/discord-messages", json=body, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code in {202, 422}
    if r.status_code == 202 and r.json() is not None:
        assert "@everyone" not in r.json()["body"].lower()
        assert "@here" not in r.json()["body"].lower()
