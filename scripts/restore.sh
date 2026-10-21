#!/usr/bin/env bash
# Rewinds the hub to a snapshot that scripts/backup.sh took (ADMIN_GUIDE.md section 13). Run as the toads user:
#
#   restore.sh list                        the snapshots kept on this server and off it
#   restore.sh <night> [options]           rewind to a snapshot: a date (2026-10-19, that day's newest) or a full name
#       --offsite                          fetch it from the off-server copy even if this server still has it
#       --db-only                          leave config/*.yaml as it is now (default: rewind it with the database)
#       --with-env                         also put back the .env files and infra/certs from the snapshot
#       --yes                              do not ask before going ahead
#   restore.sh undo                        swap back the database the last restore replaced
#
# A restore first takes a `pre-restore` snapshot, stops the services that write to the database, restores into a new
# database and only then swaps it in, keeping the replaced one as toads_previous for `undo`. It then runs the
# migrations (a snapshot from before a migration is brought up to the running code) and starts everything again.
set -euo pipefail

main() {
	REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
	# shellcheck source=scripts/backup-lib.sh
	. "$REPO/scripts/backup-lib.sh"
	cd "$REPO"
	case "${1:-}" in
	list) list ;;
	undo) shift; undo "$@" ;;
	"" | -h | --help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; [[ -n "${1:-}" ]] ;;
	-*) echo "restore: name the snapshot first (restore.sh list)" >&2; exit 64 ;;
	*) restore "$@" ;;
	esac
}

list() {
	local name
	echo "On this server ($(backup_dir)):"
	while read -r name; do
		[[ -n "$name" ]] && printf '  %s  %s\n' "$name" "$(du -sh "$(backup_dir)/$name" | cut -f1)"
	done < <(local_names)
	if offsite_enabled; then
		echo "Off the server ($(setting RESTIC_REPOSITORY | sed -E 's#^(s3:https?://[^/]+/).*#\1...#')):"
		offsite_names | sed 's/^/  /'
	else
		echo "Off the server: not set up (RESTIC_REPOSITORY in infra/.env.backup)"
	fi
}

restore() {
	local wanted="$1" offsite=false config=true env=false yes=false name path=""
	shift
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--offsite) offsite=true ;;
		--db-only) config=false ;;
		--with-env) env=true ;;
		--yes) yes=true ;;
		*) echo "restore: unknown option $1" >&2; exit 64 ;;
		esac
		shift
	done
	if [[ ! "$wanted" =~ ^[0-9TZa-z-]+$ ]]; then
		echo "restore: '$wanted' is not a date or snapshot name (restore.sh list)" >&2
		exit 64
	fi

	if [[ "$offsite" == false ]]; then
		name="$(local_names | grep -E "^${wanted}" | tail -n 1 || true)"
	fi
	if [[ -z "${name:-}" ]]; then
		offsite_enabled || { echo "restore: no snapshot '$wanted' on this server, and no off-server copy is set up" >&2; exit 66; }
		name="$(offsite_names | grep -E "^${wanted}" | tail -n 1 || true)"
		[[ -n "$name" ]] || { echo "restore: no snapshot '$wanted' here or off the server (restore.sh list)" >&2; exit 66; }
		fetch_offsite "$name"
	else
		# A hard-linked copy: a nightly backup's pruning cannot remove it while the restore runs.
		rm -rf "$(backup_dir)/.restore-$name"
		cp -al "$(backup_dir)/$name" "$(backup_dir)/.restore-$name"
	fi
	path="$(backup_dir)/.restore-$name"
	verify "$path"

	echo "restore: rewinding to $name ($(sed -n 's/^created=//p' "$path/MANIFEST"), code at $(sed -n 's/^commit=//p' "$path/MANIFEST" | cut -c1-12))"
	echo "  the database:     yes (the current one is kept as toads_previous; 'restore.sh undo' swaps it back)"
	echo "  config/*.yaml:    $([[ "$config" == true ]] && echo yes || echo "no (--db-only)")"
	echo "  .env files/certs: $([[ "$env" == true ]] && echo yes || echo "no (add --with-env)")"
	if [[ "$yes" == false ]]; then
		[[ -t 0 ]] || { echo "restore: not a terminal; add --yes to go ahead" >&2; exit 64; }
		read -r -p "Members lose every change made since then. Type yes to go ahead: " answer
		[[ "$answer" == yes ]] || { echo "restore: nothing changed"; exit 0; }
	fi

	hold_deploys
	compose up -d --wait postgres
	# Writers stop before the pre-restore snapshot, so nothing written in between is lost to both.
	stop_writers
	if [[ "$(compose exec -T postgres psql -U toads -d toads -qAt -c \
		"SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')")" == 0 ]]; then
		echo "restore: the database is empty (a new server?), so there is nothing to keep in a pre-restore snapshot"
	# On this server only: an unreachable object store must not stop a rewind from a snapshot that is already here.
	elif ! TOADS_BACKUP_LOCAL_ONLY=1 "$REPO/scripts/backup.sh" pre-restore; then
		echo "restore: the pre-restore snapshot failed, so nothing was changed. Starting the services again." >&2
		start_again || true
		exit 1
	fi
	restore_database "$path/hub.dump"
	[[ "$config" == true ]] && restore_files "$path/files.tar.gz" 'config/*.yaml'
	if [[ "$env" == true ]]; then
		restore_env "$path"
	fi
	if ! start_again; then
		echo "restore: the restored snapshot did not start; swapping the previous database back" >&2
		swap_previous
		start_again || true
		echo "restore: the database is as it was. Any config/ or .env files this restore put back stay; undo them with:" >&2
		echo "  $0 <the pre-restore snapshot above> (or fix the problem the log shows and run: $0 undo)" >&2
		exit 1
	fi
	rm -rf "$path"
	echo "restore: the hub is back at $name. To undo the database: $0 undo; to undo everything: $0 <the pre-restore snapshot above>"
}

# Swap the live database and toads_previous. Running it twice puts things back as they were.
undo() {
	if [[ "$(psql_admin -c "SELECT count(*) FROM pg_database WHERE datname = 'toads_previous'")" != 1 ]]; then
		echo "restore: there is no toads_previous database to swap back" >&2
		exit 66
	fi
	hold_deploys
	stop_writers
	swap_previous
	start_again
	echo "restore: swapped the database back; config/ and .env files were not changed (use a pre-restore snapshot for those)"
}

swap_previous() {
	disconnect toads
	psql_admin -c 'ALTER DATABASE toads RENAME TO toads_swap'
	psql_admin -c 'ALTER DATABASE toads_previous RENAME TO toads'
	psql_admin -c 'ALTER DATABASE toads_swap RENAME TO toads_previous'
}

fetch_offsite() {
	local name="$1" dir
	dir="$(backup_dir)"
	echo "restore: fetching $name from off the server"
	rm -rf "$dir/.restore-$name"
	mkdir -m 700 "$dir/.restore-$name"
	RESTIC_EXTRA_MOUNTS=(-v "$dir/.restore-$name:/restore:z")
	restic restore "latest:/snapshot" --host toads --tag "$name" --target /restore
	RESTIC_EXTRA_MOUNTS=()
}

# Every file must match the checksum taken when the snapshot was written.
verify() {
	local path="$1"
	if ! (cd "$path" && sha256sum --quiet -c SHA256SUMS); then
		echo "restore: $path does not match its checksums; try another night or --offsite" >&2
		exit 65
	fi
}

# A deploy during a restore would restart the services half-way through.
hold_deploys() {
	[[ -d "$REPO/.git" ]] || return 0
	exec 9>"$REPO/.git/deploy.lock"
	flock -n 9 || { echo "restore: a deploy is running; try again when it finishes" >&2; exit 75; }
}

stop_writers() {
	local running=() service
	for service in "${WRITERS[@]}"; do
		[[ -n "$(compose ps -q --status running "$service" 2>/dev/null)" ]] && running+=("$service")
	done
	if [[ ${#running[@]} -gt 0 ]]; then
		echo "restore: stopping ${running[*]}"
		compose stop "${running[@]}"
	fi
}

disconnect() {
	psql_admin -c "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE datname = '$1' AND pid <> pg_backend_pid()" >/dev/null
}

# Restore into toads_restore first: if that fails the live database has not been touched.
restore_database() {
	local dump="$1"
	echo "restore: loading the database"
	psql_admin -c 'DROP DATABASE IF EXISTS toads_restore'
	psql_admin -c 'CREATE DATABASE toads_restore OWNER toads'
	if ! compose exec -T postgres pg_restore -U toads -d toads_restore --no-owner --exit-on-error <"$dump"; then
		psql_admin -c 'DROP DATABASE IF EXISTS toads_restore'
		echo "restore: the dump did not load; the live database is unchanged. Starting the services again." >&2
		start_again || true
		exit 1
	fi
	disconnect toads
	psql_admin -c 'DROP DATABASE IF EXISTS toads_previous'
	psql_admin -c 'ALTER DATABASE toads RENAME TO toads_previous'
	psql_admin -c 'ALTER DATABASE toads_restore RENAME TO toads'
}

restore_files() {
	local archive="$1" members
	shift
	tar -tzf "$archive" >/dev/null || { echo "restore: cannot read $archive" >&2; return 1; }
	members="$(tar -tzf "$archive" --wildcards "$@" 2>/dev/null || true)"
	if [[ -z "$members" ]]; then
		echo "restore: the snapshot holds none of: $*"
		return 0
	fi
	# shellcheck disable=SC2086  # one member per line, none with spaces (they are our own file names)
	tar -C "$REPO" -xzf "$archive" $members
	echo "restore: put back $(echo "$members" | wc -l) files: $(echo "$members" | tr '\n' ' ')"
}

# The .env files and certificates exactly as that night (certificate files added since are removed; they are in the
# pre-restore snapshot), the database password they name, and Caddy's certificates.
restore_env() {
	local path="$1"
	find "$REPO/infra/certs" -mindepth 1 -maxdepth 1 -type f ! -name .gitkeep -delete 2>/dev/null || true
	restore_files "$path/files.tar.gz" 'infra/.env' 'services/*/.env*' 'infra/certs/*'
	match_database_password
	if [[ -f "$path/caddy_data.tar.gz" ]]; then
		compose stop caddy >/dev/null 2>&1 || true
		compose run --rm --no-deps -T --entrypoint sh caddy -c 'tar -C /data -xzf -' <"$path/caddy_data.tar.gz"
		echo "restore: put back Caddy's certificates"
	fi
	RESTART_CADDY=true
}
RESTART_CADDY=false

# The restored env files name the database password of the night they were saved (on a rebuilt server, the old
# server's). The API and worker connect with the one in TOADS_DATABASE_URL, so give the database role that one.
match_database_password() {
	local password url
	url="$(sed -n 's/^TOADS_DATABASE_URL=//p' "$REPO/services/api/.env" 2>/dev/null | tail -n 1)"
	password="$(sed -nE 's#^[a-z+]+://[^:/@]+:([^@]*)@.*#\1#p' <<<"$url")"
	[[ -n "$password" ]] || return 0
	if [[ "$password" == *%* ]]; then
		echo "restore: the restored TOADS_DATABASE_URL has a URL-encoded password; set it on the role by hand (ADMIN_GUIDE.md section 12)" >&2
		return 0
	fi
	# Sent on stdin, not as an argument, so it never shows in a process list.
	printf "ALTER ROLE toads PASSWORD '%s';\n" "${password//\'/\'\'}" | psql_admin
	echo "restore: the database password now matches the restored TOADS_DATABASE_URL"
}

# Bring the schema up to the running code, then start everything; the same order as scripts/deploy.sh.
# Returns non-zero rather than exiting, so a caller can put the previous database back.
start_again() {
	compose run --rm migrate || return 1
	compose run --rm analyser-migrate || return 1
	compose up -d || return 1
	if [[ "$RESTART_CADDY" == true ]]; then
		compose restart caddy || return 1
	fi
	local id status
	id="$(compose ps -q api)"
	for _ in $(seq 60); do
		status="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo starting)"
		[[ "$status" == healthy ]] && return 0
		sleep 2
	done
	echo "restore: the API is $status; see: docker compose -f infra/docker-compose.prod.yml logs api" >&2
	return 1
}

main "$@"
exit
