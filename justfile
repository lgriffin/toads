set dotenv-load := false

default:
    @just --list

# Install Python workspace and web dependencies
setup:
    uv sync
    cd apps/web && npm ci

# Start the dev stack (Postgres, Redis, MinIO, API, worker, web, Caddy on :8080)
up:
    for s in api worker bot; do [ -f services/$s/.env ] || cp services/$s/.env.example services/$s/.env; done
    [ -f config/raid_days.yaml ] || cp config/raid_days.example.yaml config/raid_days.yaml
    [ -f config/community.yaml ] || cp config/community.example.yaml config/community.yaml
    docker compose -f infra/docker-compose.yml up --build -d

down:
    docker compose -f infra/docker-compose.yml down

# Lint, types, Python and web tests, requirements traceability
test: lint
    uv run pytest --cov=toads_api --cov=toads_worker --cov-report=term-missing
    cd apps/web && npm run check && npm test
    just reqs

lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy packages/hub-db/src services/api/src services/worker/src services/bot/src

# Regenerate docs/requirements.md from tests/features and fail on missing IDs or persona tags
reqs:
    uv run python scripts/reqs.py
