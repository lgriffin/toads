# Shared by scripts/backup.sh and scripts/restore.sh (ADMIN_GUIDE.md section 13); sourced, never run.
# shellcheck shell=bash
# shellcheck disable=SC2034  # constants used by the scripts that source this file

# Built from infra/backup/Dockerfile (restic plus rclone); the tag names both pinned versions, so a bump rebuilds it.
RESTIC_IMAGE=toads-restic:0.18.0-rclone1.71.1
# A snapshot's name is its UTC time, plus a label for any snapshot the nightly timer did not take.
SNAPSHOT_NAME='[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z(-[a-z-]+)?'
NIGHTLY_NAME='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z$'
# Services that write to the hub database; a restore stops them first. Caddy and the web front end keep serving.
WRITERS=(api worker scheduler bot bank-bot)

# Settings live in infra/.env.backup (infra/.env.backup.example), read as plain KEY=VALUE lines and never run as shell.
backup_settings_file() { echo "$REPO/infra/.env.backup"; }

setting() {
	local key="$1" default="${2:-}" file value=""
	file="$(backup_settings_file)"
	if [[ -f "$file" ]]; then
		value="$(sed -n "s/^${key}=//p" "$file" | tail -n 1)"
	fi
	echo "${value:-$default}"
}

backup_dir() { setting TOADS_BACKUP_DIR /var/backups/toads; }

compose() { docker compose -f "$REPO/infra/docker-compose.prod.yml" "$@"; }

# psql as the database owner, connected to the maintenance database so `toads` itself can be dropped or renamed.
psql_admin() { compose exec -T -e PGOPTIONS='-c client_min_messages=warning' postgres psql -U toads -d postgres -v ON_ERROR_STOP=1 -qAt "$@"; }

offsite_enabled() { [[ -n "$(setting RESTIC_REPOSITORY)" ]]; }

# restic in a container, as the calling user so the files it restores belong to them. The settings file is its
# environment: RESTIC_REPOSITORY, RESTIC_PASSWORD and the object store's keys.
restic() {
	local dir mounts=() repository
	dir="$(backup_dir)"
	mkdir -p "$dir/.restic-cache"
	touch "$dir/.restic-cache/rclone.conf"
	repository="$(setting RESTIC_REPOSITORY)"
	# A repository on a local path (a second disk, or the drill's stand-in for object storage) is mounted as itself.
	if [[ "$repository" == /* ]]; then
		mkdir -p "$repository"
		mounts+=(-v "$repository:$repository:z")
	fi
	local extra=()
	if RCLONE_CONFIG_GDRIVE_TOKEN="$(drive_token)"; then
		export RCLONE_CONFIG_GDRIVE_TOKEN
		extra+=(-e RCLONE_CONFIG_GDRIVE_TOKEN)
	fi
	if ! docker image inspect "$RESTIC_IMAGE" >/dev/null 2>&1; then
		docker build -q -t "$RESTIC_IMAGE" "$REPO/infra/backup" >/dev/null
	fi
	# rclone (for a Google Drive repository) reads its remote from RCLONE_CONFIG_* in the settings file and keeps
	# refreshed sign-in tokens in the cache folder.
	docker run --rm -i --user "$(id -u):$(id -g)" --env-file "$(backup_settings_file)" \
		-e RESTIC_CACHE_DIR=/cache -e RCLONE_CONFIG=/cache/rclone.conf -v "$dir/.restic-cache:/cache:z" \
		"${extra[@]}" "${mounts[@]}" "${RESTIC_EXTRA_MOUNTS[@]}" "$RESTIC_IMAGE" "$@"
}

# `rclone authorize` run with options prints the Drive token wrapped as base64 JSON ({"token":"{...}"}, starting eyJ).
# Prints the plain {"access_token":"..."} JSON when RCLONE_CONFIG_GDRIVE_TOKEN holds the wrapped form (even pasted
# inside braces), so it can be passed by environment over the file's value; fails when there is nothing to unwrap.
drive_token() {
	local token
	token="$(setting RCLONE_CONFIG_GDRIVE_TOKEN)"
	[[ "$token" != *'"access_token":"'* && "$token" =~ eyJ[A-Za-z0-9_-]+ ]] || return 1
	unwrap_rclone_token "${BASH_REMATCH[0]}"
}

# Unpadded URL-safe base64 of {"token":"<the token's JSON, quotes escaped>"} to the token's JSON.
unwrap_rclone_token() {
	local s="${1//-/+}"
	s="${s//_//}"
	while ((${#s} % 4)); do s+="="; done
	base64 -d <<<"$s" | sed -E 's/^\{"token":"(.*)"\}$/\1/; s/\\"/"/g'
}
RESTIC_EXTRA_MOUNTS=()

# Snapshot names kept off the server, oldest first.
offsite_names() {
	local json
	json="$(restic snapshots --host toads --tag toads --json)"
	grep -oE "\"${SNAPSHOT_NAME}\"" <<<"$json" | tr -d '"' | sort -u || true
}

# Snapshot names kept on this server, oldest first.
local_names() {
	local dir
	dir="$(backup_dir)"
	[[ -d "$dir" ]] || return 0
	find "$dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | grep -E "^${SNAPSHOT_NAME}$" | sort || true
}

# Post a one-line alert to the Discord webhook in TOADS_BACKUP_ALERT_WEBHOOK, if there is one. Never fails.
alert() {
	local webhook message="$1"
	webhook="$(setting TOADS_BACKUP_ALERT_WEBHOOK)"
	[[ -n "$webhook" ]] || return 0
	message="${message//[\"\\]/}"
	curl -fsS -m 15 -H 'Content-Type: application/json' -d "{\"content\":\"${message}\"}" "$webhook" >/dev/null 2>&1 ||
		echo "backup: could not post the alert to TOADS_BACKUP_ALERT_WEBHOOK" >&2
}
