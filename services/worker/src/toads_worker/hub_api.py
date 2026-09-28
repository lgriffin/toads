"""Posting to the hub API with the worker's service token. Every job that hands the hub a page goes through here."""

from __future__ import annotations

from typing import Any

import httpx

from toads_worker.settings import Settings


def service_token(settings: Settings) -> str:
    """The token the hub API expects on /api/worker/*. Checked before any work, so a misconfigured worker fails fast."""
    token = settings.hub_service_token.get_secret_value()
    if not token:
        raise RuntimeError("TOADS_HUB_SERVICE_TOKEN is not set; the hub API would refuse the page")
    return token


def put(settings: Settings, path: str, body: dict[str, Any], hub: httpx.Client | None = None) -> dict[str, Any]:
    """PUT `body` to the hub API and return its JSON answer; raises on any non-2xx answer."""
    token = service_token(settings)
    hub = hub or httpx.Client(base_url=settings.hub_api_url, timeout=30.0)
    r = hub.put(path, json=body, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    answer: dict[str, Any] = r.json()
    return answer
