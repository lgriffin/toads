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
    key=$(just credentials-key); for s in api worker; do sed -i.bak "s|^TOADS_CREDENTIALS_KEYS=replace-me$|TOADS_CREDENTIALS_KEYS=$key|" services/$s/.env && rm services/$s/.env.bak; done
    [ -f config/raid_days.yaml ] || cp config/raid_days.example.yaml config/raid_days.yaml
    [ -f config/community.yaml ] || cp config/community.example.yaml config/community.yaml
    [ -f config/raid_sheets.yaml ] || cp config/raid_sheets.example.yaml config/raid_sheets.yaml
    docker compose -f infra/docker-compose.yml up --build -d

# Print a new key for TOADS_CREDENTIALS_KEYS (encrypts members' own Warcraft Logs keys)
credentials-key:
    @uv run python -c "from hub_db import CredentialCipher; print(CredentialCipher.generate_key())"

down:
    docker compose -f infra/docker-compose.yml down

# Every CI check that needs no network, Docker or database, fastest first (scripts/dev.py check)
check:
    uv run python scripts/dev.py check

# Lint, types, Python and web tests, requirements traceability
test: check

# Ruff fixes and formatting
fix:
    uv run python scripts/dev.py fix

# Any scripts/dev.py tasks, in order, e.g. `just dev types test`
dev *tasks:
    uv run python scripts/dev.py {{tasks}}

lint:
    uv run python scripts/dev.py format lint imports types

# Regenerate docs/requirements.md from tests/features and fail on missing IDs or persona tags
reqs:
    uv run python scripts/reqs.py
