# syntax=docker/dockerfile:1
# Build from the repo root: docker build -f services/worker/Dockerfile .
# TODO(2.0): pin both base images by digest before the first tagged release (REQ-DEV-SUP-001).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /src
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# git fetches wcl-core, wcl-store and wcl-app, which uv.lock pins to one warcraftlogs_project commit.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY services ./services
RUN uv sync --frozen --no-dev --package toads-worker

FROM python:3.12-slim-bookworm
RUN useradd --system --uid 10001 toads
COPY --from=build /src/.venv /app/.venv
COPY --from=build /src/packages /src/packages
COPY --from=build /src/services /src/services
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER toads


CMD ["toads-worker"]
