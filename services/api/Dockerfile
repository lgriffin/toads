# syntax=docker/dockerfile:1
# Build from the repo root: docker build -f services/api/Dockerfile .
# TODO(2.0): pin both base images by digest before the first tagged release (REQ-DEV-SUP-001).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /src
# The venv is built at the path the runtime stage uses: console scripts keep an absolute shebang to it.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
# git fetches wcl-core, which uv.lock pins to a warcraftlogs_project commit.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY services ./services
RUN uv sync --frozen --no-dev --package toads-api

FROM python:3.12-slim-bookworm
RUN useradd --system --uid 10001 toads
COPY --from=build /app/.venv /app/.venv
COPY --from=build /src/packages /src/packages
COPY --from=build /src/services /src/services
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER toads
EXPOSE 8000
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["uvicorn", "toads_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
