#!/usr/bin/env bash
# Deploys one commit of main on the production server (docs/deploy.md). The deploy workflow runs it over SSH as the
# deploy key's forced command, passing the commit sha; run it by hand with a sha, or none for the latest main.
# Migrations run before any container is replaced, so a failed migration leaves the current site serving
# (REQ-DEV-REL-002). Everything sits in main() because the checkout below rewrites this file while it runs.
set -euo pipefail

main() {
	local repo sha target
	repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
	sha="${1:-${SSH_ORIGINAL_COMMAND:-}}"
	if [[ -n "$sha" && ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
		echo "deploy: expected a full commit sha, got '$sha'" >&2
		exit 64
	fi
	cd "$repo"
	if ! grep -Eq '^TOADS_POSTGRES_PASSWORD=.+' infra/.env 2>/dev/null; then
		echo "deploy: infra/.env needs TOADS_POSTGRES_PASSWORD (scripts/server-setup.sh writes it)" >&2
		exit 78
	fi

	exec 9>"$repo/.git/deploy.lock"
	flock -n 9 || { echo "deploy: another deploy is running" >&2; exit 75; }

	git fetch --quiet origin main
	target="$(git rev-parse --verify "${sha:-origin/main}^{commit}")"
	if ! git merge-base --is-ancestor "$target" origin/main; then
		echo "deploy: $target is not on main" >&2
		exit 65
	fi
	git checkout --quiet --detach "$target"
	echo "deploy: $(git log -1 --format='%h %s')"

	local compose=(docker compose -f infra/docker-compose.prod.yml)
	"${compose[@]}" build --pull
	"${compose[@]}" run --rm migrate
	"${compose[@]}" run --rm analyser-migrate
	"${compose[@]}" up -d --remove-orphans

	local service id status
	for service in api web; do
		id="$("${compose[@]}" ps -q "$service")"
		for _ in $(seq 60); do
			status="$(docker inspect -f '{{.State.Health.Status}}' "$id")"
			[[ "$status" == healthy ]] && break
			sleep 2
		done
		if [[ "$status" != healthy ]]; then
			echo "deploy: $service is $status; see: docker compose -f infra/docker-compose.prod.yml logs $service" >&2
			exit 1
		fi
	done

	docker image prune -f >/dev/null
	echo "$(date -u +%FT%TZ) $target" >>"$repo/.git/deploy.log"
	echo "deploy: $target is live"
}

main "$@"
exit
